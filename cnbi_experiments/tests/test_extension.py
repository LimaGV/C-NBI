import unittest
import numpy as np
from cnbi.payoff import individual_payoff
from cnbi.rsm import z, dz
from cnbi.combinations import simplex_weights
from cnbi_experiments.doe import RSM, design, design_jac, master_design
from cnbi_experiments.benchmarks import MaF
from cnbi_experiments.solver import Config, Meter, BudgetExhausted, payoff, uncertainty_pa, run_cnbi, cnbi_deltas
from cnbi.spectral import parallel_analysis


class Extension(unittest.TestCase):
    def test_vrf_minimum_two_and_retention(self):
        from cnbi_experiments.comparators import vrf_factor_count, rotated_factor_scores, run_vrf
        self.assertEqual(vrf_factor_count([.95, .98, 1.]), 2)
        self.assertEqual(vrf_factor_count([.5, .90, 1.]), 2)
        self.assertEqual(vrf_factor_count([.4, .7, .85, .96, 1.]), 4)
        with self.assertRaises(ValueError):
            vrf_factor_count([1.])
        Y = np.random.default_rng(9).normal(size=(100, 4))
        scores, L, W, mean, scale, _ = rotated_factor_scores(Y, 2)
        np.testing.assert_allclose(scores, ((Y-mean)/scale)@L@np.linalg.pinv(L.T@L), atol=1e-12)
        # Regression: VRF must use the quadratic response surfaces and Eq. 21,
        # rather than applying NBI directly to signed factor scores.
        result = run_vrf(MaF(9, 6), Config(budget=50000, seed=101))
        self.assertIn(result['status'], ('COMPLETED', 'BUDGET_EXHAUSTED'))
        self.assertGreaterEqual(result['diagnostics']['n_factors'], 2)
        self.assertGreaterEqual(result['diagnostics']['retained_variance'], .90)
        self.assertEqual(result['diagnostics']['implementation'],
                         'Pereira_et_al_2025_equations_11_17_to_28')
        self.assertEqual(result['diagnostics']['score_weight_rule'], 'L@pinv(L.T@L)')
        self.assertGreater(len(result['rows']), 0)

    def test_maf9_payoff_uses_distinct_line_minima(self):
        problem = MaF(9, 6)
        X, P = payoff(problem, Meter(problem, 10000), Config(seed=101))
        self.assertEqual(len(np.unique(np.round(X, 9), axis=0)), problem.m)
        np.testing.assert_allclose(np.diag(P), 0., atol=1e-8)

    def test_design_and_replication(self):
        rows = master_design()
        self.assertEqual(len(rows), 270)
        self.assertEqual(len(set(r['scenario_id'] for r in rows)), 27)
        for nx in (2, 3, 5):
            x = np.arange(nx)/10
            J = design_jac(x)
            for j in range(nx):
                h = np.eye(nx)[j]*1e-6
                np.testing.assert_allclose((design(x+h)-design(x-h))[0]/2e-6, J[:, j], atol=1e-9)
        x = np.array([.2, .3, -.1])
        np.testing.assert_array_equal(design(x)[0], z(x))
        np.testing.assert_array_equal(design_jac(x), dz(x))
        self.assertEqual(len(simplex_weights(6, .5)), 21)
        deltas = cnbi_deltas(Config())
        self.assertEqual(deltas[2], .2)
        self.assertEqual(deltas[3], .2)
        self.assertEqual(deltas[4], .2)
        self.assertEqual(deltas[5], .5)
        self.assertEqual(deltas[6], .5)
        self.assertEqual(len(simplex_weights(2, deltas[2])), 6)
        self.assertEqual(len(simplex_weights(3, deltas[3])), 21)

    def test_payoff_and_pa_reuse_three_dimensions(self):
        A = .4*np.array([[1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1.]])
        problem = RSM(A, 101)
        cfg = Config(maxiter=500)
        X, P = payoff(problem, Meter(problem, 10000), cfg)
        X0, P0 = individual_payoff(problem.B)
        np.testing.assert_allclose(X, X0, atol=1e-9, rtol=1e-9)
        np.testing.assert_allclose(P, P0, atol=1e-9, rtol=1e-9)
        pa = uncertainty_pa(problem, P0, X0)
        legacy = parallel_analysis(P0, X0, problem.mse, problem.XtX_inv)
        for key in ('d', 's', 'p95', 'floor', 'ceiling', 'scaled'):
            np.testing.assert_array_equal(pa[key], legacy[key])

    def test_hard_budget_and_reproducibility(self):
        p = MaF(8, 4)
        meter = Meter(p, 2)
        meter([0, 0]); meter([0, 1])
        with self.assertRaises(BudgetExhausted):
            meter([1, 0])
        self.assertEqual(meter.used, 2)
        cfg = Config(budget=300, seed=101)
        a, b = run_cnbi(p, cfg, 'all'), run_cnbi(p, cfg, 'all')
        self.assertEqual(a['evaluations'], b['evaluations'])
        self.assertEqual(a['status'], b['status'])
        self.assertLessEqual(a['evaluations'], 300)
        for ra, rb in zip(a['rows'], b['rows']):
            if 'F' in ra:
                np.testing.assert_array_equal(ra['F'], rb['F'])
        with self.assertRaises(ValueError):
            run_cnbi(p, cfg, 'direct')

    def test_unlimited_meter_and_population_scaled_ea_budget(self):
        from cnbi_experiments.comparators import ea_budget
        p = MaF(8, 4)
        meter = Meter(p, None)
        for _ in range(10):
            meter([0, 0])
        self.assertEqual(meter.used, 10)
        self.assertEqual(ea_budget(4), 50000)
        self.assertEqual(ea_budget(11), 400400)

    def test_degenerate_payoff_has_explicit_status(self):
        class DuplicateObjectives:
            nx, m = 2, 2
            lower, upper = np.zeros(2), np.ones(2)
            def evaluate(self, x):
                value = np.sum(np.asarray(x)**2)
                return np.array([value, value])
            def jacobian(self, x):
                return np.vstack([2*np.asarray(x), 2*np.asarray(x)])
            def feasible(self, X):
                X = np.atleast_2d(X)
                return np.all((X >= 0) & (X <= 1), axis=1)
        result = run_cnbi(DuplicateObjectives(), Config(budget=500), 'all')
        self.assertEqual(result['status'], 'NO_NONDEGENERATE_COMBINATIONS')
        self.assertEqual(result['rows'], [])
