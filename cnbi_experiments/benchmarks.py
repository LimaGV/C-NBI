"""Cheng et al. (2017), equations 16, 17, 38--40; see references/provenance.json.

Independent Python equations checked against official BIMK/PlatEMO source.
MaF13 uses D=5 and n=D in eq.39 (the article switches notation).
Only its first three PF coordinates lie on the unit sphere; the repeated
remaining coordinates are the nonlinear embedding in eq.38.
"""
import numpy as np


def polygon_contains(X, vertices, tolerance=1e-12):
    """Ray crossing with explicit boundary inclusion (PlatEMO inpolygon)."""
    X = np.atleast_2d(X)
    inside = np.zeros(len(X), bool)
    boundary = inside.copy()
    for a, b in zip(vertices, np.roll(vertices, -1, axis=0)):
        e = b-a
        v = X-a
        cross = e[0]*v[:, 1]-e[1]*v[:, 0]
        dot = v@e
        boundary |= ((np.abs(cross) <= tolerance*max(1., np.linalg.norm(e))) &
                     (dot >= -tolerance) & (dot <= e@e+tolerance))
        if e[1] != 0:
            crossing = ((a[1] > X[:, 1]) != (b[1] > X[:, 1]))
            inside ^= crossing & (X[:, 0] < a[0]+(X[:, 1]-a[1])*e[0]/e[1])
    return inside | boundary


class MaF:
    def __init__(self, number, m):
        if number not in (8, 9, 13) or not isinstance(m, int) or m < 3:
            raise ValueError('MaF number must be 8, 9 or 13; M must be integer >=3')
        self.number, self.m = number, m
        self.nx = 5 if number == 13 else 2
        self.name = f'MaF{number}'
        self.lower = np.array([0., 0., -2., -2., -2.]) if number == 13 else np.full(2, -10000.)
        self.upper = np.array([1., 1., 2., 2., 2.]) if number == 13 else np.full(2, 10000.)
        theta = np.pi/2 - np.arange(1, m+1)*2*np.pi/m
        self.vertices = np.column_stack([np.cos(theta), np.sin(theta)])
        self.invalid_polygons = []
        if number == 9:
            # Zero-based translation of PlatEMO head/tail construction.
            for gap in range(1, int(np.ceil(m/2-2))+1):
                for head in range(m):
                    tail = head+gap
                    a, b, c, d = self.vertices[np.array([head-1, head, tail, tail+1]) % m]
                    t = np.linalg.solve(np.column_stack([b-a, -(d-c)]), c-a)[0]
                    origin = a+t*(b-a)
                    arc = self.vertices[np.arange(head, tail+1) % m]
                    self.invalid_polygons.append(np.vstack([arc, 2*origin-arc]))

    def _array(self, X):
        X = np.asarray(X, float)
        if X.ndim not in (1, 2) or X.shape[-1] != self.nx or not np.isfinite(X).all():
            raise ValueError(f'Expected finite (...,{self.nx}) decisions')
        return np.atleast_2d(X)

    def feasible(self, X):
        X = self._array(X)
        valid = np.all((X >= self.lower) & (X <= self.upper), axis=1)
        if self.number == 9:
            forbidden = np.zeros(len(X), bool)
            for polygon in self.invalid_polygons:
                forbidden |= polygon_contains(X, polygon)
            valid &= ~forbidden | polygon_contains(X, self.vertices)
        return valid

    @staticmethod
    def _convex_inside_margin(X, vertices):
        """Positive inside a convex polygon, zero on its boundary."""
        X = np.atleast_2d(X)
        edge = np.roll(vertices, -1, axis=0)-vertices
        area2 = np.sum(vertices[:, 0]*np.roll(vertices[:, 1], -1)-
                       vertices[:, 1]*np.roll(vertices[:, 0], -1))
        orientation = 1. if area2 >= 0 else -1.
        v = X[:, None, :]-vertices[None, :, :]
        cross = orientation*(edge[None, :, 0]*v[:, :, 1]-edge[None, :, 1]*v[:, :, 0])
        return np.min(cross/np.linalg.norm(edge, axis=1)[None, :], axis=1)

    def feasibility_margin(self, X):
        """Continuous MaF9 feasibility margin for constrained optimizers.

        Feasible means inside the central polygon OR outside every forbidden
        polygon. It encodes the exact same set tested by ``feasible``; only the
        representation supplied to SLSQP is new.
        """
        X = self._array(X)
        bound_margin = np.min(np.minimum(X-self.lower, self.upper-X), axis=1)
        if self.number != 9:
            return bound_margin
        central = self._convex_inside_margin(X, self.vertices)
        outside_all = np.full(len(X), np.inf)
        for polygon in self.invalid_polygons:
            outside_all = np.minimum(outside_all, -self._convex_inside_margin(X, polygon))
        region_margin = np.maximum(central, outside_all)
        return np.minimum(bound_margin, region_margin)

    def evaluate(self, X):
        """Raw objective equation, like CalObj: feasibility is a separate operation.

        Never repair inside deterministic evaluation: this would change the
        decision being evaluated by SLSQP. Use repair explicitly for EAs.
        """
        scalar = np.asarray(X).ndim == 1
        X = self._array(X)
        if self.number == 8:
            F = np.linalg.norm(X[:, None, :]-self.vertices, axis=2)
        elif self.number == 9:
            edge = np.roll(self.vertices, -1, axis=0)-self.vertices
            v = X[:, None, :]-self.vertices
            F = np.abs(edge[:, 0]*v[:, :, 1]-edge[:, 1]*v[:, :, 0])/np.linalg.norm(edge, axis=1)
        else:
            Y = X-2*X[:, 1, None]*np.sin(2*np.pi*X[:, 0, None]+np.arange(1, 6)*np.pi/5)
            a, b = X[:, 0]*np.pi/2, X[:, 1]*np.pi/2
            F = np.empty((len(X), self.m))
            F[:, 0] = np.sin(a)+2*Y[:, 3]**2
            F[:, 1] = np.cos(a)*np.sin(b)+2*Y[:, 4]**2
            F[:, 2] = np.cos(a)*np.cos(b)+2*Y[:, 2]**2
            F[:, 3:] = (F[:, 0]**2+F[:, 1]**10+F[:, 2]**10+
                        np.sum(Y[:, 3:]**2, axis=1))[:, None]
        return F[0] if scalar else F

    def jacobian(self, x):
        """Analytic M x D Jacobian of the published objective equations.

        At the nondifferentiable zero-distance points of MaF8/9, the zero
        subgradient is used. This avoids spending objective evaluations on
        numerical differences without changing any objective or constraint.
        """
        x = self._array(x)[0]
        if self.number == 8:
            delta = x-self.vertices
            distance = np.linalg.norm(delta, axis=1)
            return np.divide(delta, distance[:, None], out=np.zeros_like(delta),
                             where=distance[:, None] > 1e-15)
        if self.number == 9:
            edge = np.roll(self.vertices, -1, axis=0)-self.vertices
            v = x-self.vertices
            cross = edge[:, 0]*v[:, 1]-edge[:, 1]*v[:, 0]
            direction = np.column_stack([-edge[:, 1], edge[:, 0]])/np.linalg.norm(edge, axis=1)[:, None]
            return np.sign(cross)[:, None]*direction
        phi = 2*np.pi*x[0]+np.arange(1, 6)*np.pi/5
        Y = x-2*x[1]*np.sin(phi)
        dY = np.zeros((5, 5))
        dY[:, 0] = -4*np.pi*x[1]*np.cos(phi)
        dY[:, 1] = -2*np.sin(phi)
        dY[np.arange(5), np.arange(5)] += 1
        a, b = x[0]*np.pi/2, x[1]*np.pi/2
        J = np.zeros((self.m, 5))
        J[0, 0] = np.pi/2*np.cos(a)
        J[0] += 4*Y[3]*dY[3]
        J[1, 0] = -np.pi/2*np.sin(a)*np.sin(b)
        J[1, 1] = np.pi/2*np.cos(a)*np.cos(b)
        J[1] += 4*Y[4]*dY[4]
        J[2, 0] = -np.pi/2*np.sin(a)*np.cos(b)
        J[2, 1] = -np.pi/2*np.cos(a)*np.sin(b)
        J[2] += 4*Y[2]*dY[2]
        F = self.evaluate(x)
        extra = (2*F[0]*J[0]+10*F[1]**9*J[1]+10*F[2]**9*J[2]+
                 2*Y[3]*dY[3]+2*Y[4]*dY[4])
        J[3:] = extra
        return J

    def optimization_starts(self, seed):
        """Normative-geometry starts plus seeded domain starts.

        These improve numerical access to known individual minima but do not
        bypass optimization or inject a payoff value into CNBI.
        """
        rng = np.random.default_rng(seed)
        if self.number in (8, 9):
            geometric = [np.zeros(2), *self.vertices]
        else:
            linked = []
            for x1, x2 in ((0., 0.), (1., 0.), (0., .5), (0., 1.)):
                x = np.zeros(5); x[:2] = (x1, x2)
                x[2:] = 2*x2*np.sin(2*np.pi*x1+np.arange(3, 6)*np.pi/5)
                linked.append(x)
            geometric = linked
        return geometric+list(rng.uniform(self.lower, self.upper, (2*self.nx, self.nx)))

    def payoff_starts(self, objective, seed):
        """Objective-aware starts for non-unique MaF9 line minima."""
        if self.number != 9:
            return self.optimization_starts(seed)
        midpoint = (self.vertices[objective]+self.vertices[(objective+1) % self.m])/2
        remaining = [(self.vertices[j]+self.vertices[(j+1) % self.m])/2
                     for j in range(self.m) if j != objective]
        return [midpoint, self.vertices[objective], self.vertices[(objective+1) % self.m],
                np.zeros(2), *remaining]

    def payoff_key(self, objective, result):
        """Unique deterministic representative among MaF9's infinite minima."""
        if self.number == 9:
            minimum_class = 0 if float(result.fun) <= 1e-10 else 1
            return minimum_class, float(result.x@result.x), float(result.fun)
        return (float(result.fun),)

    def repair(self, X, seed):
        X = self._array(X).copy()
        rng = np.random.default_rng(seed)
        for _ in range(10000):
            invalid = ~self.feasible(X)
            if not invalid.any():
                return X
            X[invalid] = rng.uniform(self.lower, self.upper, (invalid.sum(), self.nx))
        raise RuntimeError('MaF repair exceeded its explicit safety limit')

    def pareto_sample(self, n, seed):
        """Exactly n draws on normative PS; uniform polygon area / sphere area.

        MaF8/9: equal-area fan triangles, uniform barycentric points.
        MaF13: normalized absolute Gaussian triples (uniform spherical octant),
        inverse spherical map and linked x3..x5. No optimizer or dominated cloud.
        """
        if n < 1:
            raise ValueError('n must be positive')
        rng = np.random.default_rng(seed)
        if self.number != 13:
            ids = rng.integers(self.m, size=n)
            u = np.sqrt(rng.random(n))[:, None]
            v = rng.random(n)[:, None]
            X = u*((1-v)*self.vertices[ids]+v*self.vertices[(ids+1) % self.m])
        else:
            S = np.abs(rng.normal(size=(n, 3)))
            S /= np.linalg.norm(S, axis=1, keepdims=True)
            X = np.empty((n, 5))
            X[:, 0] = 2/np.pi*np.arcsin(S[:, 0])
            X[:, 1] = 2/np.pi*np.arctan2(S[:, 1], S[:, 2])
            X[:, 2:] = 2*X[:, 1, None]*np.sin(2*np.pi*X[:, 0, None]+np.arange(3, 6)*np.pi/5)
        return X, self.evaluate(X)
