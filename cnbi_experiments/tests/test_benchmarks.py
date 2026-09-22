import math
import unittest
import numpy as np
from cnbi_experiments.benchmarks import MaF, polygon_contains
from cnbi_experiments.parallel_analysis import permutation_pa, sequential_rank, payoff_window


class Benchmarks(unittest.TestCase):
    def test_analytic_jacobians(self):
        probes = [(MaF(8, 6), np.array([.13, -.21])),
                  (MaF(9, 6), np.array([.13, -.21])),
                  (MaF(13, 8), np.array([.17, .23, .05, .10, .15]))]
        for problem, x in probes:
            numerical = np.empty((problem.m, problem.nx))
            for j in range(problem.nx):
                h = 1e-7
                step = np.zeros(problem.nx); step[j] = h
                numerical[:, j] = (problem.evaluate(x+step)-problem.evaluate(x-step))/(2*h)
            np.testing.assert_allclose(problem.jacobian(x), numerical, rtol=2e-6, atol=2e-7)
            self.assertTrue(all(problem.feasible(s)[0] for s in problem.optimization_starts(101)
                                if np.all((s >= problem.lower) & (s <= problem.upper))))
    def test_polygon_analytic(self):
        for m in (4, 6, 8, 10, 15):
            p, q = MaF(8, m), MaF(9, m)
            np.testing.assert_allclose(p.evaluate([0, 0]), 1, atol=1e-14)
            np.testing.assert_allclose(q.evaluate([0, 0]), math.cos(math.pi/m), atol=1e-14)
            # Circumcircle chord length, independent of the distance code.
            expected = [2*abs(math.sin(math.pi*j/m)) for j in range(m)]
            np.testing.assert_allclose(p.evaluate(p.vertices[0]), expected, atol=2e-14)
            for problem in (p, q):
                X, F = problem.pareto_sample(101, 2026)
                self.assertEqual(F.shape, (101, m))
                self.assertTrue(problem.feasible(X).all())
                self.assertTrue(np.isfinite(F).all())
                self.assertFalse(problem.feasible([[10001, 0]])[0])
        # Infinite line distance, not distance to the edge segment.
        np.testing.assert_allclose(MaF(9, 4).evaluate([2, 0]),
                                   [1/math.sqrt(2), 3/math.sqrt(2), 3/math.sqrt(2), 1/math.sqrt(2)], atol=1e-14)

    def test_maf9_forbidden(self):
        p = MaF(9, 6)
        self.assertEqual(len(p.invalid_polygons), 6)
        # Interior point of first reflected polygon, outside central hexagon.
        X = np.array([[1., -math.sqrt(3)], [0., 0.]])
        self.assertEqual(p.feasible(X).tolist(), [False, True])
        repaired = p.repair(X, 11)
        self.assertTrue(p.feasible(repaired).all())
        np.testing.assert_array_equal(repaired, p.repair(X, 11))
        self.assertTrue(polygon_contains([[0, 0]], np.array([[0, 0], [1, 0], [0, 1]]))[0])
        probes = np.array([[1., -math.sqrt(3)], [0., 0.], p.vertices[0]])
        margin = p.feasibility_margin(probes)
        self.assertLess(margin[0], 0)
        self.assertGreater(margin[1], 0)
        self.assertGreaterEqual(margin[2], -1e-12)
        np.testing.assert_array_equal(margin >= -1e-12, p.feasible(probes))
        for j in range(p.m):
            midpoint = p.payoff_starts(j, 101)[0]
            self.assertTrue(p.feasible(midpoint)[0])
            self.assertAlmostEqual(p.evaluate(midpoint)[j], 0., places=14)

    def test_maf13_published_equations_scalar(self):
        # Scalar, 1-based J sets calculated independently from eq.38--40.
        for m in (4, 6, 8, 10, 15):
            p = MaF(13, m)
            self.assertEqual(p.nx, 5)
            for x in ([0, 0, 0, 0, 0], [0, 0, .5, -.25, 1.], [.37, .81, -1.2, .4, 1.7]):
                y = {j: x[j-1]-2*x[1]*math.sin(2*math.pi*x[0]+j*math.pi/5) for j in range(3, 6)}
                f = [math.sin(math.pi*x[0]/2)+2*y[4]**2,
                     math.cos(math.pi*x[0]/2)*math.sin(math.pi*x[1]/2)+2*y[5]**2,
                     math.cos(math.pi*x[0]/2)*math.cos(math.pi*x[1]/2)+2*y[3]**2]
                f += [f[0]**2+f[1]**10+f[2]**10+y[4]**2+y[5]**2]*(m-3)
                np.testing.assert_allclose(p.evaluate(x), f, rtol=3e-14, atol=1e-14)
            X, F = p.pareto_sample(500, 23)
            self.assertTrue(p.feasible(X).all())
            np.testing.assert_allclose(np.sum(F[:, :3]**2, axis=1), 1, atol=1e-14)
            np.testing.assert_allclose(F[:, 3], F[:, 0]**2+F[:, 1]**10+F[:, 2]**10, atol=1e-14)
            np.testing.assert_array_equal(F[:, 3:], np.repeat(F[:, 3:4], m-3, axis=1))
        with self.assertRaises(ValueError):
            MaF(13, 8).evaluate(np.zeros(12))


class Horn(unittest.TestCase):
    def test_sequential_and_reproducible(self):
        self.assertEqual(sequential_rank([4, 1, 2], [2, 1, 1]), 1)
        F = np.random.default_rng(5).normal(size=(100, 4))
        F[:, 3] = F[:, 0]
        a, b = permutation_pa(F, B=31, seed=42), permutation_pa(F, B=31, seed=42)
        np.testing.assert_array_equal(a['null_spectra'], b['null_spectra'])
        np.testing.assert_allclose(a['observed'].sum(), 4)
        np.testing.assert_allclose(a['null_spectra'].sum(axis=1), 4)
        self.assertGreaterEqual(a['rank'], 1)
        with self.assertRaises(ValueError):
            permutation_pa(np.ones((10, 3)))
        with self.assertRaises(ValueError):
            payoff_window(np.eye(4), 0)


if __name__ == '__main__':
    unittest.main()
