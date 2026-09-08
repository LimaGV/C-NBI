"""Regression against original source, independent invariants and saved results.

No tolerance is introduced for original-versus-refactored calculations.
"""
from pathlib import Path
import ast
import inspect
import json
import math
import unittest

import numpy as np
from cnbi import core, rsm, payoff, spectral, combinations, nbi, pareto
from cnbi.config import ALPHA, DELTA_BY_K

FIXTURES = Path(__file__).parent / "fixtures"
ORIGINAL = {}
exec(compile((FIXTURES / "original_core.py.txt").read_text(encoding="utf-8"),
             "original_core.py.txt", "exec"), ORIGINAL)
ORIGINAL_PARETO = {}
exec(compile((FIXTURES / "original_nondominated.py.txt").read_text(encoding="utf-8"),
             "original_nondominated.py.txt", "exec"), ORIGINAL_PARETO)


def model(name="m4_low_seed103"):
    data = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    return tuple(np.array(data[key], dtype=float) for key in ("B", "mse", "XtX_inv"))


def assert_equal(test, left, right):
    if isinstance(left, np.ndarray):
        np.testing.assert_array_equal(left, right, strict=True)
    elif isinstance(left, dict):
        test.assertEqual(left.keys(), right.keys())
        for key in left:
            assert_equal(test, left[key], right[key])
    elif isinstance(left, (list, tuple)):
        test.assertEqual(type(left), type(right))
        test.assertEqual(len(left), len(right))
        for a, b in zip(left, right):
            assert_equal(test, a, b)
    elif isinstance(left, (float, np.floating)) and np.isnan(left):
        test.assertTrue(np.isnan(right))
    else:
        test.assertEqual(left, right)


def computational_ast(source):
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if ast.get_docstring(node) is not None:
                node.body.pop(0)
    return ast.dump(tree, include_attributes=False)


class StructuralTests(unittest.TestCase):
    def test_all_extracted_function_bodies_match_original_ast(self):
        original_tree = ast.parse((FIXTURES / "original_core.py.txt").read_text(encoding="utf-8"))
        definitions = {node.name: ast.unparse(node) for node in original_tree.body
                       if isinstance(node, ast.FunctionDef)}
        intentionally_parameterized = {'cnbi', 'individual_payoff', '_solve_nbi_base'}
        for module in (core, rsm, payoff, spectral, combinations, nbi):
            for name, function in inspect.getmembers(module, inspect.isfunction):
                if function.__module__ != module.__name__ or name in intentionally_parameterized or name not in definitions:
                    continue
                with self.subTest(function=name):
                    self.assertEqual(computational_ast(inspect.getsource(function)),
                                     computational_ast(definitions[name]))

    def test_pareto_zero_tolerance_matches_notebook04_exactly(self):
        rng = np.random.default_rng(90210)
        for rows in (0, 1, 8, 31):
            F = rng.normal(size=(rows, 4))
            np.testing.assert_array_equal(
                pareto.nondominated(F, tol=0),
                ORIGINAL_PARETO['nondominated'](F),
            )

    def test_exact_pareto_dominance_and_duplicates(self):
        F = np.array([[1, 2], [2, 1], [2, 2], [1, 2]], dtype=float)
        np.testing.assert_array_equal(pareto.nondominated(F), [True, True, False, True])

    def test_configurable_payoff_starts(self):
        starts = payoff.canonical_payoff_starts()
        self.assertEqual(len(starts), 7)
        self.assertTrue(all(start.shape == (3,) for start in starts))
        B, _, _ = model()
        X, P = payoff.individual_payoff(B, starts=starts[:1], maxiter=600)
        self.assertEqual(X.shape, (4, 3))
        self.assertEqual(P.shape, (4, 4))

    def test_optional_postprocessing_estimated_or_real(self):
        X = np.array([[0, 0], [.4e-5, 0], [1, 1], [2, 2]], float)
        F_estimated = np.array([[1, 3], [.5, 3], [2, 2], [3, 3]], float)
        estimated = pareto.postprocess_frontier(
            X, F_estimated, duplicate_tolerance=1e-5, dominance_tolerance=1e-10
        )
        np.testing.assert_array_equal(estimated['indices'], [1, 2])
        self.assertEqual(estimated['input_count'], 4)
        self.assertEqual(estimated['after_duplicates'], 3)
        # Mesmos X, avaliação externa diferente: a fronteira real pode mudar.
        F_real = np.array([[1, 1], [1.1, 1.1], [.8, 2], [3, 3]], float)
        real = pareto.postprocess_frontier(
            X, F_real, duplicate_tolerance=1e-5, dominance_tolerance=.05
        )
        np.testing.assert_array_equal(real['indices'], [0, 2])

    def test_nbi_iteration_and_rescue_limits_are_configurable(self):
        B, _, _ = model()
        X, P = payoff.individual_payoff(B)
        rows, _, _ = nbi._solve_nbi_base(
            B[:, :2], B, np.arange(2), X[:2], P[:2, :2],
            .5, maxiter=1, max_rescues=0,
        )
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(
            not attempt['start'].startswith('rescue_')
            for row in rows for attempt in row['attempt_log']
        ))

    def test_fixed_configuration(self):
        self.assertEqual(ALPHA, ORIGINAL["ALPHA"])
        self.assertEqual(DELTA_BY_K, ORIGINAL["DELTA_BY_K"])

    def test_simplex_cardinality_vertices_and_order(self):
        for k in (2, 3, 4, 5):
            delta = DELTA_BY_K[k]
            weights = combinations.simplex_weights(k, delta)
            self.assertEqual(len(weights), math.comb(round(1/delta)+k-1, k-1))
            np.testing.assert_array_equal(weights, ORIGINAL["simplex_weights"](k, delta))
            self.assertTrue(np.all(weights >= 0))
            # Floating sums have roundoff; existing np.isclose convention, no new solver tolerance.
            self.assertTrue(np.all(np.isclose(weights.sum(1), 1)))
            for vertex in np.eye(k):
                self.assertTrue(np.any(np.all(weights == vertex, axis=1)))
            assert_equal(self, combinations._nearest_weight_order(weights),
                         ORIGINAL["_nearest_weight_order"](weights))

    def test_quadratic_basis_and_exact_derivative(self):
        x = np.array([.5, -.25, .75])
        np.testing.assert_array_equal(rsm.z(x), [1,.5,-.25,.75,.25,.0625,.5625,-.125,.375,-.1875])
        # A centered difference of a quadratic has no truncation term; binary step is exact here.
        step = 2.0**-10
        derivative = np.column_stack([(rsm.z(x+step*e)-rsm.z(x-step*e))/(2*step) for e in np.eye(3)])
        np.testing.assert_array_equal(rsm.dz(x), derivative)


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs = {}
        for name in ("m4_low_seed103", "m6_medium_seed101", "m12_high_seed101"):
            B, mse, inverse = model(name)
            X, P = payoff.individual_payoff(B)
            ref_X, ref_P = ORIGINAL["individual_payoff"](B)
            actual = core.cnbi(B, P, X, mse, inverse)
            expected = ORIGINAL["cnbi"](B, ref_P, ref_X, mse, inverse)
            cls.runs[name] = (B, mse, inverse, X, P, ref_X, ref_P, actual, expected)

    def test_all_candidates_diagnostics_statuses_counts_exact(self):
        for name, run in self.runs.items():
            with self.subTest(scenario=name):
                assert_equal(self, run[7], run[8])
                self.assertGreater(len(run[7][0]), 0)

    def test_payoff_orientation_and_values(self):
        for name, (B, mse, inv, X, P, ref_X, ref_P, actual, expected) in self.runs.items():
            with self.subTest(scenario=name):
                np.testing.assert_array_equal(X, ref_X)
                np.testing.assert_array_equal(P, ref_P)
                # Same evaluation operation, independently assemble anchors in rows.
                rows = np.vstack([rsm.z(x) @ B for x in X])
                np.testing.assert_array_equal(P, rows.T)
                self.assertTrue(np.all(np.sum(X*X, axis=1) <= ALPHA**2+1e-7))

    def test_global_chim_svd_and_selection(self):
        for name, run in self.runs.items():
            B, _, _, _, P = run[:5]
            rows, pa = run[7]
            ideal = P.min(1)
            amp = np.where(P.max(1)-ideal > 1e-12, P.max(1)-ideal, 1)
            scaled = (P-ideal[:, None])/amp[:, None]
            np.testing.assert_array_equal(pa['scaled'], scaled)
            edges = scaled.T[1:]-scaled.T[:1]
            np.testing.assert_array_equal(pa['s'], np.linalg.svd(edges, compute_uv=False))
            import itertools
            selected = []
            for k in range(2, min(B.shape[1], 4)+1):
                for combo in itertools.combinations(range(B.shape[1]), k):
                    A = scaled[np.ix_(combo, combo)].T
                    s = np.linalg.svd(A[1:]-A[:1], compute_uv=False)
                    q = np.inf if s[-1] <= 1e-12 else s[0]/s[-1]
                    if s[-1] > pa['floor'] and q <= pa['ceiling']:
                        selected.append(combo)
            self.assertEqual(list(dict.fromkeys(r['combo'] for r in rows)), selected)
            self.assertEqual(len(rows), sum(math.comb(round(1/DELTA_BY_K[len(c)])+len(c)-1, len(c)-1) for c in selected))

    def test_recomposition_acceptance_and_exact_anchors(self):
        for name, run in self.runs.items():
            B, _, _, X, P = run[:5]
            for row in run[7][0]:
                np.testing.assert_array_equal(row['F_rsm'], rsm.z(row['x']) @ B)
                if row['accepted'] and row['start'] != 'payoff_anchor_exact':
                    self.assertLessEqual(row['eq_inf'], 1e-5)
                    self.assertLessEqual(row['sphere_violation'], 1e-8)
                if row['start'] == 'payoff_anchor_exact':
                    idx = row['combo'][int(np.argmax(row['beta']))]
                    np.testing.assert_array_equal(row['x'], X[idx])

    def test_local_nbi_equation_with_existing_acceptance_bound(self):
        B, _, _, _, P, _, _, actual, _ = self.runs['m4_low_seed103']
        from scipy.linalg import null_space
        for row in actual[0]:
            if not row['accepted']:
                continue
            idx = np.array(row['combo'])
            sub = P[np.ix_(idx, idx)]
            ideal = sub.min(1)
            amp = np.maximum(sub.max(1)-ideal, 1e-12)
            A = ((sub-ideal[:, None])/amp[:, None]).T
            normal = null_space(A[1:]-A[:1]).ravel()
            normal /= np.linalg.norm(normal)
            if normal @ (-A.mean(0)) < 0:
                normal = -normal
            residual = (rsm.z(row['x']) @ B[:, idx]-ideal)/amp - (row['beta'] @ A+row.get('t', 0)*normal)
            self.assertLessEqual(np.max(np.abs(residual)), 1e-5)

    def test_repeat_is_deterministic_and_global_rng_unchanged(self):
        B, mse, inv, X, P, _, _, actual, _ = self.runs['m4_low_seed103']
        state = np.random.get_state()
        repeated = core.cnbi(B, P, X, mse, inv)
        assert_equal(self, actual, repeated)
        assert_equal(self, state, np.random.get_state())

    def test_historical_checkpoint_exact(self):
        historical = FIXTURES/'historical_m4_low_seed103.npz'
        self.assertTrue(historical.exists(), 'Historical reference must be present')
        rows, pa = self.runs['m4_low_seed103'][7]
        with np.load(historical, allow_pickle=False) as data:
            np.testing.assert_array_equal(np.vstack([r['x'] for r in rows]), data['X'])
            np.testing.assert_array_equal(np.vstack([r['F_rsm'] for r in rows]), data['F_rsm'])
            for field in ['success','k','beta_id','eq_inf','sphere_violation','start','attempts','execution_order','accepted','solver_success','subproblem_status']:
                np.testing.assert_array_equal(np.array([r[field] for r in rows]), data[field])
            for i, row in enumerate(rows):
                self.assertEqual(list(row['combo']), json.loads(str(data['combo_json'][i])))
                np.testing.assert_array_equal(row['beta'], json.loads(str(data['beta_json'][i])))
                self.assertEqual(row.get('t', 0.), data['t'][i])
                self.assertEqual(row['attempt_log'], json.loads(str(data['attempt_log_json'][i])))


if __name__ == '__main__':
    unittest.main()
