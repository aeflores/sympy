from typing import Tuple

from sympy.core.add import Add
from sympy.core.basic import sympify, cacheit
from sympy.core.expr import Expr
from sympy.core.function import Function, ArgumentIndexError, PoleError, expand_mul
from sympy.core.logic import fuzzy_not, fuzzy_or, FuzzyBool
from sympy.core.numbers import igcdex, Rational, pi
from sympy.core.relational import Ne
from sympy.core.singleton import S
from sympy.core.symbol import Symbol
from sympy.functions.combinatorial.factorials import factorial, RisingFactorial
from sympy.functions.elementary.exponential import log, exp
from sympy.functions.elementary.integers import floor
from sympy.functions.elementary.hyperbolic import (acoth, asinh, atanh, cosh,
    coth, HyperbolicFunction, sinh, tanh)
from sympy.functions.elementary.miscellaneous import sqrt, Min, Max
from sympy.functions.elementary.piecewise import Piecewise
from sympy.sets.sets import FiniteSet
from sympy.utilities.iterables import numbered_symbols

###############################################################################
########################## TRIGONOMETRIC FUNCTIONS ############################
###############################################################################


class TrigonometricFunction(Function):
    """Base class for trigonometric functions. """

    unbranched = True
    _singularities = (S.ComplexInfinity,)

    def _eval_is_rational(self):
        s = self.func(*self.args)
        if s.func == self.func:
            if s.args[0].is_rational and fuzzy_not(s.args[0].is_zero):
                return False
        else:
            return s.is_rational

    def _eval_is_algebraic(self):
        s = self.func(*self.args)
        if s.func == self.func:
            if fuzzy_not(self.args[0].is_zero) and self.args[0].is_algebraic:
                return False
            pi_coeff = _pi_coeff(self.args[0])
            if pi_coeff is not None and pi_coeff.is_rational:
                return True
        else:
            return s.is_algebraic

    def _eval_expand_complex(self, deep=True, **hints):
        re_part, im_part = self.as_real_imag(deep=deep, **hints)
        return re_part + im_part*S.ImaginaryUnit

    def _as_real_imag(self, deep=True, **hints):
        if self.args[0].is_extended_real:
            if deep:
                hints['complex'] = False
                return (self.args[0].expand(deep, **hints), S.Zero)
            else:
                return (self.args[0], S.Zero)
        if deep:
            re, im = self.args[0].expand(deep, **hints).as_real_imag()
        else:
            re, im = self.args[0].as_real_imag()
        return (re, im)

    def _period(self, general_period, symbol=None):
        f = expand_mul(self.args[0])
        if symbol is None:
            symbol = tuple(f.free_symbols)[0]

        if not f.has(symbol):
            return S.Zero

        if f == symbol:
            return general_period

        if symbol in f.free_symbols:
            if f.is_Mul:
                g, h = f.as_independent(symbol)
                if h == symbol:
                    return general_period/abs(g)

            if f.is_Add:
                a, h = f.as_independent(symbol)
                g, h = h.as_independent(symbol, as_Add=False)
                if h == symbol:
                    return general_period/abs(g)

        raise NotImplementedError("Use the periodicity function instead.")


def _peeloff_pi(arg):
    """
    Split ARG into two parts, a "rest" and a multiple of pi/2.
    This assumes ARG to be an Add.
    The multiple of pi returned in the second position is always a Rational.

    Examples
    ========

    >>> from sympy.functions.elementary.trigonometric import _peeloff_pi as peel
    >>> from sympy import pi
    >>> from sympy.abc import x, y
    >>> peel(x + pi/2)
    (x, pi/2)
    >>> peel(x + 2*pi/3 + pi*y)
    (x + pi*y + pi/6, pi/2)

    """
    pi_coeff = S.Zero
    rest_terms = []
    for a in Add.make_args(arg):
        K = a.coeff(S.Pi)
        if K and K.is_rational:
            pi_coeff += K
        else:
            rest_terms.append(a)

    if pi_coeff is S.Zero:
        return arg, S.Zero

    m1 = (pi_coeff % S.Half)*S.Pi
    m2 = pi_coeff*S.Pi - m1
    final_coeff = m2 / S.Pi
    if final_coeff.is_integer or ((2*final_coeff).is_integer
        and final_coeff.is_even is False):
            return Add(*(rest_terms + [m1])), m2
    return arg, S.Zero


def _pi_coeff(arg, cycles=1):
    """
    When arg is a Number times pi (e.g. 3*pi/2) then return the Number
    normalized to be in the range [0, 2], else None.

    When an even multiple of pi is encountered, if it is multiplying
    something with known parity then the multiple is returned as 0 otherwise
    as 2.

    Examples
    ========

    >>> from sympy.functions.elementary.trigonometric import _pi_coeff as coeff
    >>> from sympy import pi, Dummy
    >>> from sympy.abc import x
    >>> coeff(3*x*pi)
    3*x
    >>> coeff(11*pi/7)
    11/7
    >>> coeff(-11*pi/7)
    3/7
    >>> coeff(4*pi)
    0
    >>> coeff(5*pi)
    1
    >>> coeff(5.0*pi)
    1
    >>> coeff(5.5*pi)
    3/2
    >>> coeff(2 + pi)

    >>> coeff(2*Dummy(integer=True)*pi)
    2
    >>> coeff(2*Dummy(even=True)*pi)
    0

    """
    arg = sympify(arg)
    if arg is S.Pi:
        return S.One
    elif not arg:
        return S.Zero
    elif arg.is_Mul:
        cx = arg.coeff(S.Pi)
        if cx:
            c, x = cx.as_coeff_Mul()  # pi is not included as coeff
            if c.is_Float:
                # recast exact binary fractions to Rationals
                f = abs(c) % 1
                if f != 0:
                    p = -int(round(log(f, 2).evalf()))
                    m = 2**p
                    cm = c*m
                    i = int(cm)
                    if i == cm:
                        c = Rational(i, m)
                        cx = c*x
                else:
                    c = Rational(int(c))
                    cx = c*x
            if x.is_integer:
                c2 = c % 2
                if c2 == 1:
                    return x
                elif not c2:
                    if x.is_even is not None:  # known parity
                        return S.Zero
                    return S(2)
                else:
                    return c2*x
            return cx
    elif arg.is_zero:
        return S.Zero


class sin(TrigonometricFunction):
    """
    The sine function.

    Returns the sine of x (measured in radians).

    Explanation
    ===========

    This function will evaluate automatically in the
    case x/pi is some rational number [4]_.  For example,
    if x is a multiple of pi, pi/2, pi/3, pi/4 and pi/6.

    Examples
    ========

    >>> from sympy import sin, pi
    >>> from sympy.abc import x
    >>> sin(x**2).diff(x)
    2*x*cos(x**2)
    >>> sin(1).diff(x)
    0
    >>> sin(pi)
    0
    >>> sin(pi/2)
    1
    >>> sin(pi/6)
    1/2
    >>> sin(pi/12)
    -sqrt(2)/4 + sqrt(6)/4


    See Also
    ========

    csc, cos, sec, tan, cot
    asin, acsc, acos, asec, atan, acot, atan2

    References
    ==========

    .. [1] https://en.wikipedia.org/wiki/Trigonometric_functions
    .. [2] http://dlmf.nist.gov/4.14
    .. [3] http://functions.wolfram.com/ElementaryFunctions/Sin
    .. [4] http://mathworld.wolfram.com/TrigonometryAngles.html

    """

    def period(self, symbol=None):
        return self._period(2*pi, symbol)

    def fdiff(self, argindex=1):
        if argindex == 1:
            return cos(self.args[0])
        else:
            raise ArgumentIndexError(self, argindex)

    @classmethod
    def eval(cls, arg):
        from sympy.calculus import AccumBounds
        from sympy.sets.setexpr import SetExpr
        if arg.is_Number:
            if arg is S.NaN:
                return S.NaN
            elif arg.is_zero:
                return S.Zero
            elif arg is S.Infinity or arg is S.NegativeInfinity:
                return AccumBounds(-1, 1)

        if arg is S.ComplexInfinity:
            return S.NaN

        if isinstance(arg, AccumBounds):
            min, max = arg.min, arg.max
            d = floor(min/(2*S.Pi))
            if min is not S.NegativeInfinity:
                min = min - d*2*S.Pi
            if max is not S.Infinity:
                max = max - d*2*S.Pi
            if AccumBounds(min, max).intersection(FiniteSet(S.Pi/2, S.Pi*Rational(5, 2))) \
                    is not S.EmptySet and \
                    AccumBounds(min, max).intersection(FiniteSet(S.Pi*Rational(3, 2),
                        S.Pi*Rational(7, 2))) is not S.EmptySet:
                return AccumBounds(-1, 1)
            elif AccumBounds(min, max).intersection(FiniteSet(S.Pi/2, S.Pi*Rational(5, 2))) \
                    is not S.EmptySet:
                return AccumBounds(Min(sin(min), sin(max)), 1)
            elif AccumBounds(min, max).intersection(FiniteSet(S.Pi*Rational(3, 2), S.Pi*Rational(8, 2))) \
                        is not S.EmptySet:
                return AccumBounds(-1, Max(sin(min), sin(max)))
            else:
                return AccumBounds(Min(sin(min), sin(max)),
                                Max(sin(min), sin(max)))
        elif isinstance(arg, SetExpr):
            return arg._eval_func(cls)

        if arg.could_extract_minus_sign():
            return -cls(-arg)

        i_coeff = arg.as_coefficient(S.ImaginaryUnit)
        if i_coeff is not None:
            return S.ImaginaryUnit*sinh(i_coeff)

        pi_coeff = _pi_coeff(arg)
        if pi_coeff is not None:
            if pi_coeff.is_integer:
                return S.Zero

            if (2*pi_coeff).is_integer:
                # is_even-case handled above as then pi_coeff.is_integer,
                # so check if known to be not even
                if pi_coeff.is_even is False:
                    return S.NegativeOne**(pi_coeff - S.Half)

            if not pi_coeff.is_Rational:
                narg = pi_coeff*S.Pi
                if narg != arg:
                    return cls(narg)
                return None

            # https://github.com/sympy/sympy/issues/6048
            # transform a sine to a cosine, to avoid redundant code
            if pi_coeff.is_Rational:
                x = pi_coeff % 2
                if x > 1:
                    return -cls((x % 1)*S.Pi)
                if 2*x > 1:
                    return cls((1 - x)*S.Pi)
                narg = ((pi_coeff + Rational(3, 2)) % 2)*S.Pi
                result = cos(narg)
                if not isinstance(result, cos):
                    return result
                if pi_coeff*S.Pi != arg:
                    return cls(pi_coeff*S.Pi)
                return None

        if arg.is_Add:
            x, m = _peeloff_pi(arg)
            if m:
                return sin(m)*cos(x) + cos(m)*sin(x)

        if arg.is_zero:
            return S.Zero

        if isinstance(arg, asin):
            return arg.args[0]

        if isinstance(arg, atan):
            x = arg.args[0]
            return x/sqrt(1 + x**2)

        if isinstance(arg, atan2):
            y, x = arg.args
            return y/sqrt(x**2 + y**2)

        if isinstance(arg, acos):
            x = arg.args[0]
            return sqrt(1 - x**2)

        if isinstance(arg, acot):
            x = arg.args[0]
            return 1/(sqrt(1 + 1/x**2)*x)

        if isinstance(arg, acsc):
            x = arg.args[0]
            return 1/x

        if isinstance(arg, asec):
            x = arg.args[0]
            return sqrt(1 - 1/x**2)

    @staticmethod
    @cacheit
    def taylor_term(n, x, *previous_terms):
        if n < 0 or n % 2 == 0:
            return S.Zero
        else:
            x = sympify(x)

            if len(previous_terms) > 2:
                p = previous_terms[-2]
                return -p*x**2/(n*(n - 1))
            else:
                return (-1)**(n//2)*x**(n)/factorial(n)

    def _eval_nseries(self, x, n, logx, cdir=0):
        arg = self.args[0]
        if logx is not None:
            arg = arg.subs(log(x), logx)
        if arg.subs(x, 0).has(S.NaN, S.ComplexInfinity):
            raise PoleError("Cannot expand %s around 0" % (self))
        return Function._eval_nseries(self, x, n=n, logx=logx, cdir=cdir)

    def _eval_rewrite_as_exp(self, arg, **kwargs):
        I = S.ImaginaryUnit
        if isinstance(arg, (TrigonometricFunction, HyperbolicFunction)):
            arg = arg.func(arg.args[0]).rewrite(exp)
        return (exp(arg*I) - exp(-arg*I))/(2*I)

    def _eval_rewrite_as_Pow(self, arg, **kwargs):
        if isinstance(arg, log):
            I = S.ImaginaryUnit
            x = arg.args[0]
            return I*x**-I/2 - I*x**I /2

    def _eval_rewrite_as_cos(self, arg, **kwargs):
        return cos(arg - S.Pi/2, evaluate=False)

    def _eval_rewrite_as_tan(self, arg, **kwargs):
        tan_half = tan(S.Half*arg)
        return 2*tan_half/(1 + tan_half**2)

    def _eval_rewrite_as_sincos(self, arg, **kwargs):
        return sin(arg)*cos(arg)/cos(arg)

    def _eval_rewrite_as_cot(self, arg, **kwargs):
        cot_half = cot(S.Half*arg)
        return 2*cot_half/(1 + cot_half**2)

    def _eval_rewrite_as_pow(self, arg, **kwargs):
        return self.rewrite(cos).rewrite(pow)

    def _eval_rewrite_as_sqrt(self, arg, **kwargs):
        return self.rewrite(cos).rewrite(sqrt)

    def _eval_rewrite_as_csc(self, arg, **kwargs):
        return 1/csc(arg)

    def _eval_rewrite_as_sec(self, arg, **kwargs):
        return 1/sec(arg - S.Pi/2, evaluate=False)

    def _eval_rewrite_as_sinc(self, arg, **kwargs):
        return arg*sinc(arg)

    def _eval_conjugate(self):
        return self.func(self.args[0].conjugate())

    def as_real_imag(self, deep=True, **hints):
        re, im = self._as_real_imag(deep=deep, **hints)
        return (sin(re)*cosh(im), cos(re)*sinh(im))

    def _eval_expand_trig(self, **hints):
        from sympy.functions.special.polynomials import chebyshevt, chebyshevu
        arg = self.args[0]
        x = None
        if arg.is_Add:  # TODO, implement more if deep stuff here
            # TODO: Do this more efficiently for more than two terms
            x, y = arg.as_two_terms()
            sx = sin(x, evaluate=False)._eval_expand_trig()
            sy = sin(y, evaluate=False)._eval_expand_trig()
            cx = cos(x, evaluate=False)._eval_expand_trig()
            cy = cos(y, evaluate=False)._eval_expand_trig()
            return sx*cy + sy*cx
        elif arg.is_Mul:
            n, x = arg.as_coeff_Mul(rational=True)
            if n.is_Integer:  # n will be positive because of .eval
                # canonicalization

                # See http://mathworld.wolfram.com/Multiple-AngleFormulas.html
                if n.is_odd:
                    return (-1)**((n - 1)/2)*chebyshevt(n, sin(x))
                else:
                    return expand_mul((-1)**(n/2 - 1)*cos(x)*chebyshevu(n -
                        1, sin(x)), deep=False)
            pi_coeff = _pi_coeff(arg)
            if pi_coeff is not None:
                if pi_coeff.is_Rational:
                    return self.rewrite(sqrt)
        return sin(arg)

    def _eval_as_leading_term(self, x, logx=None, cdir=0):
        from sympy import re
        from sympy.calculus.util import AccumBounds
        arg = self.args[0]
        x0 = arg.subs(x, 0).cancel()
        n = x0/S.Pi
        if n.is_integer:
            lt = (arg - n*S.Pi).as_leading_term(x)
            return ((-1)**n)*lt
        if x0 is S.ComplexInfinity:
            x0 = arg.limit(x, 0, dir='-' if re(cdir).is_negative else '+')
        if x0 in [S.Infinity, S.NegativeInfinity]:
            return AccumBounds(-1, 1)
        return self.func(x0) if x0.is_finite else self

    def _eval_is_extended_real(self):
        if self.args[0].is_extended_real:
            return True

    def _eval_is_finite(self):
        arg = self.args[0]
        if arg.is_extended_real:
            return True

    def _eval_is_zero(self):
        arg = self.args[0]
        if arg.is_zero:
            return True

    def _eval_is_complex(self):
        if self.args[0].is_extended_real \
                or self.args[0].is_complex:
            return True


class cos(TrigonometricFunction):
    """
    The cosine function.

    Returns the cosine of x (measured in radians).

    Explanation
    ===========

    See :func:`sin` for notes about automatic evaluation.

    Examples
    ========

    >>> from sympy import cos, pi
    >>> from sympy.abc import x
    >>> cos(x**2).diff(x)
    -2*x*sin(x**2)
    >>> cos(1).diff(x)
    0
    >>> cos(pi)
    -1
    >>> cos(pi/2)
    0
    >>> cos(2*pi/3)
    -1/2
    >>> cos(pi/12)
    sqrt(2)/4 + sqrt(6)/4

    See Also
    ========

    sin, csc, sec, tan, cot
    asin, acsc, acos, asec, atan, acot, atan2

    References
    ==========

    .. [1] https://en.wikipedia.org/wiki/Trigonometric_functions
    .. [2] http://dlmf.nist.gov/4.14
    .. [3] http://functions.wolfram.com/ElementaryFunctions/Cos

    """

    def period(self, symbol=None):
        return self._period(2*pi, symbol)

    def fdiff(self, argindex=1):
        if argindex == 1:
            return -sin(self.args[0])
        else:
            raise ArgumentIndexError(self, argindex)

    @classmethod
    def eval(cls, arg):
        from sympy.functions.special.polynomials import chebyshevt
        from sympy.calculus.util import AccumBounds
        from sympy.sets.setexpr import SetExpr
        if arg.is_Number:
            if arg is S.NaN:
                return S.NaN
            elif arg.is_zero:
                return S.One
            elif arg is S.Infinity or arg is S.NegativeInfinity:
                # In this case it is better to return AccumBounds(-1, 1)
                # rather than returning S.NaN, since AccumBounds(-1, 1)
                # preserves the information that sin(oo) is between
                # -1 and 1, where S.NaN does not do that.
                return AccumBounds(-1, 1)

        if arg is S.ComplexInfinity:
            return S.NaN

        if isinstance(arg, AccumBounds):
            return sin(arg + S.Pi/2)
        elif isinstance(arg, SetExpr):
            return arg._eval_func(cls)

        if arg.is_extended_real and arg.is_finite is False:
            return AccumBounds(-1, 1)

        if arg.could_extract_minus_sign():
            return cls(-arg)

        i_coeff = arg.as_coefficient(S.ImaginaryUnit)
        if i_coeff is not None:
            return cosh(i_coeff)

        pi_coeff = _pi_coeff(arg)
        if pi_coeff is not None:
            if pi_coeff.is_integer:
                return (S.NegativeOne)**pi_coeff

            if (2*pi_coeff).is_integer:
                # is_even-case handled above as then pi_coeff.is_integer,
                # so check if known to be not even
                if pi_coeff.is_even is False:
                    return S.Zero

            if not pi_coeff.is_Rational:
                narg = pi_coeff*S.Pi
                if narg != arg:
                    return cls(narg)
                return None

            # cosine formula #####################
            # https://github.com/sympy/sympy/issues/6048
            # explicit calculations are performed for
            # cos(k pi/n) for n = 8,10,12,15,20,24,30,40,60,120
            # Some other exact values like cos(k pi/240) can be
            # calculated using a partial-fraction decomposition
            # by calling cos( X ).rewrite(sqrt)
            cst_table_some = {
                3: S.Half,
                5: (sqrt(5) + 1)/4,
            }
            if pi_coeff.is_Rational:
                q = pi_coeff.q
                p = pi_coeff.p % (2*q)
                if p > q:
                    narg = (pi_coeff - 1)*S.Pi
                    return -cls(narg)
                if 2*p > q:
                    narg = (1 - pi_coeff)*S.Pi
                    return -cls(narg)

                # If nested sqrt's are worse than un-evaluation
                # you can require q to be in (1, 2, 3, 4, 6, 12)
                # q <= 12, q=15, q=20, q=24, q=30, q=40, q=60, q=120 return
                # expressions with 2 or fewer sqrt nestings.
                table2 = {
                    12: (3, 4),
                    20: (4, 5),
                    30: (5, 6),
                    15: (6, 10),
                    24: (6, 8),
                    40: (8, 10),
                    60: (20, 30),
                    120: (40, 60)
                    }
                if q in table2:
                    a, b = p*S.Pi/table2[q][0], p*S.Pi/table2[q][1]
                    nvala, nvalb = cls(a), cls(b)
                    if None == nvala or None == nvalb:
                        return None
                    return nvala*nvalb + cls(S.Pi/2 - a)*cls(S.Pi/2 - b)

                if q > 12:
                    return None

                if q in cst_table_some:
                    cts = cst_table_some[pi_coeff.q]
                    return chebyshevt(pi_coeff.p, cts).expand()

                if 0 == q % 2:
                    narg = (pi_coeff*2)*S.Pi
                    nval = cls(narg)
                    if None == nval:
                        return None
                    x = (2*pi_coeff + 1)/2
                    sign_cos = (-1)**((-1 if x < 0 else 1)*int(abs(x)))
                    return sign_cos*sqrt( (1 + nval)/2 )
            return None

        if arg.is_Add:
            x, m = _peeloff_pi(arg)
            if m:
                return cos(m)*cos(x) - sin(m)*sin(x)

        if arg.is_zero:
            return S.One

        if isinstance(arg, acos):
            return arg.args[0]

        if isinstance(arg, atan):
            x = arg.args[0]
            return 1/sqrt(1 + x**2)

        if isinstance(arg, atan2):
            y, x = arg.args
            return x/sqrt(x**2 + y**2)

        if isinstance(arg, asin):
            x = arg.args[0]
            return sqrt(1 - x ** 2)

        if isinstance(arg, acot):
            x = arg.args[0]
            return 1/sqrt(1 + 1/x**2)

        if isinstance(arg, acsc):
            x = arg.args[0]
            return sqrt(1 - 1/x**2)

        if isinstance(arg, asec):
            x = arg.args[0]
            return 1/x

    @staticmethod
    @cacheit
    def taylor_term(n, x, *previous_terms):
        if n < 0 or n % 2 == 1:
            return S.Zero
        else:
            x = sympify(x)

            if len(previous_terms) > 2:
                p = previous_terms[-2]
                return -p*x**2/(n*(n - 1))
            else:
                return (-1)**(n//2)*x**(n)/factorial(n)

    def _eval_nseries(self, x, n, logx, cdir=0):
        arg = self.args[0]
        if logx is not None:
            arg = arg.subs(log(x), logx)
        if arg.subs(x, 0).has(S.NaN, S.ComplexInfinity):
            raise PoleError("Cannot expand %s around 0" % (self))
        return Function._eval_nseries(self, x, n=n, logx=logx, cdir=cdir)

    def _eval_rewrite_as_exp(self, arg, **kwargs):
        I = S.ImaginaryUnit
        if isinstance(arg, (TrigonometricFunction, HyperbolicFunction)):
            arg = arg.func(arg.args[0]).rewrite(exp)
        return (exp(arg*I) + exp(-arg*I))/2

    def _eval_rewrite_as_Pow(self, arg, **kwargs):
        if isinstance(arg, log):
            I = S.ImaginaryUnit
            x = arg.args[0]
            return x**I/2 + x**-I/2

    def _eval_rewrite_as_sin(self, arg, **kwargs):
        return sin(arg + S.Pi/2, evaluate=False)

    def _eval_rewrite_as_tan(self, arg, **kwargs):
        tan_half = tan(S.Half*arg)**2
        return (1 - tan_half)/(1 + tan_half)

    def _eval_rewrite_as_sincos(self, arg, **kwargs):
        return sin(arg)*cos(arg)/sin(arg)

    def _eval_rewrite_as_cot(self, arg, **kwargs):
        cot_half = cot(S.Half*arg)**2
        return (cot_half - 1)/(cot_half + 1)

    def _eval_rewrite_as_pow(self, arg, **kwargs):
        return self._eval_rewrite_as_sqrt(arg)

    def _eval_rewrite_as_sqrt(self, arg, **kwargs):
        from sympy.functions.special.polynomials import chebyshevt

        def migcdex(x):
            # recursive calcuation of gcd and linear combination
            # for a sequence of integers.
            # Given  (x1, x2, x3)
            # Returns (y1, y1, y3, g)
            # such that g is the gcd and x1*y1+x2*y2+x3*y3 - g = 0
            # Note, that this is only one such linear combination.
            if len(x) == 1:
                return (1, x[0])
            if len(x) == 2:
                return igcdex(x[0], x[-1])
            g = migcdex(x[1:])
            u, v, h = igcdex(x[0], g[-1])
            return tuple([u] + [v*i for i in g[0:-1] ] + [h])

        def ipartfrac(r, factors=None):
            from sympy.ntheory import factorint
            if isinstance(r, int):
                return r
            if not isinstance(r, Rational):
                raise TypeError("r is not rational")
            n = r.q
            if 2 > r.q*r.q:
                return r.q

            if None == factors:
                a = [n//x**y for x, y in factorint(r.q).items()]
            else:
                a = [n//x for x in factors]
            if len(a) == 1:
                return [ r ]
            h = migcdex(a)
            ans = [ r.p*Rational(i*j, r.q) for i, j in zip(h[:-1], a) ]
            assert r == sum(ans)
            return ans
        pi_coeff = _pi_coeff(arg)
        if pi_coeff is None:
            return None

        if pi_coeff.is_integer:
            # it was unevaluated
            return self.func(pi_coeff*S.Pi)

        if not pi_coeff.is_Rational:
            return None

        def _cospi257():
            """ Express cos(pi/257) explicitly as a function of radicals
                Based upon the equations in
                http://math.stackexchange.com/questions/516142/how-does-cos2-pi-257-look-like-in-real-radicals
                See also http://www.susqu.edu/brakke/constructions/257-gon.m.txt
            """
            def f1(a, b):
                return (a + sqrt(a**2 + b))/2, (a - sqrt(a**2 + b))/2

            def f2(a, b):
                return (a - sqrt(a**2 + b))/2

            t1, t2 = f1(-1, 256)
            z1, z3 = f1(t1, 64)
            z2, z4 = f1(t2, 64)
            y1, y5 = f1(z1, 4*(5 + t1 + 2*z1))
            y6, y2 = f1(z2, 4*(5 + t2 + 2*z2))
            y3, y7 = f1(z3, 4*(5 + t1 + 2*z3))
            y8, y4 = f1(z4, 4*(5 + t2 + 2*z4))
            x1, x9 = f1(y1, -4*(t1 + y1 + y3 + 2*y6))
            x2, x10 = f1(y2, -4*(t2 + y2 + y4 + 2*y7))
            x3, x11 = f1(y3, -4*(t1 + y3 + y5 + 2*y8))
            x4, x12 = f1(y4, -4*(t2 + y4 + y6 + 2*y1))
            x5, x13 = f1(y5, -4*(t1 + y5 + y7 + 2*y2))
            x6, x14 = f1(y6, -4*(t2 + y6 + y8 + 2*y3))
            x15, x7 = f1(y7, -4*(t1 + y7 + y1 + 2*y4))
            x8, x16 = f1(y8, -4*(t2 + y8 + y2 + 2*y5))
            v1 = f2(x1, -4*(x1 + x2 + x3 + x6))
            v2 = f2(x2, -4*(x2 + x3 + x4 + x7))
            v3 = f2(x8, -4*(x8 + x9 + x10 + x13))
            v4 = f2(x9, -4*(x9 + x10 + x11 + x14))
            v5 = f2(x10, -4*(x10 + x11 + x12 + x15))
            v6 = f2(x16, -4*(x16 + x1 + x2 + x5))
            u1 = -f2(-v1, -4*(v2 + v3))
            u2 = -f2(-v4, -4*(v5 + v6))
            w1 = -2*f2(-u1, -4*u2)
            return sqrt(sqrt(2)*sqrt(w1 + 4)/8 + S.Half)

        cst_table_some = {
            3: S.Half,
            5: (sqrt(5) + 1)/4,
            17: sqrt((15 + sqrt(17))/32 + sqrt(2)*(sqrt(17 - sqrt(17)) +
                sqrt(sqrt(2)*(-8*sqrt(17 + sqrt(17)) - (1 - sqrt(17))
                *sqrt(17 - sqrt(17))) + 6*sqrt(17) + 34))/32),
            257: _cospi257()
            # 65537 is the only other known Fermat prime and the very
            # large expression is intentionally omitted from SymPy; see
            # http://www.susqu.edu/brakke/constructions/65537-gon.m.txt
        }

        def _fermatCoords(n):
            # if n can be factored in terms of Fermat primes with
            # multiplicity of each being 1, return those primes, else
            # False
            primes = []
            for p_i in cst_table_some:
                quotient, remainder = divmod(n, p_i)
                if remainder == 0:
                    n = quotient
                    primes.append(p_i)
                    if n == 1:
                        return tuple(primes)
            return False

        if pi_coeff.q in cst_table_some:
            rv = chebyshevt(pi_coeff.p, cst_table_some[pi_coeff.q])
            if pi_coeff.q < 257:
                rv = rv.expand()
            return rv

        if not pi_coeff.q % 2:  # recursively remove factors of 2
            pico2 = pi_coeff*2
            nval = cos(pico2*S.Pi).rewrite(sqrt)
            x = (pico2 + 1)/2
            sign_cos = -1 if int(x) % 2 else 1
            return sign_cos*sqrt( (1 + nval)/2 )

        FC = _fermatCoords(pi_coeff.q)
        if FC:
            decomp = ipartfrac(pi_coeff, FC)
            X = [(x[1], x[0]*S.Pi) for x in zip(decomp, numbered_symbols('z'))]
            pcls = cos(sum([x[0] for x in X]))._eval_expand_trig().subs(X)
            return pcls.rewrite(sqrt)
        else:
            decomp = ipartfrac(pi_coeff)
            X = [(x[1], x[0]*S.Pi) for x in zip(decomp, numbered_symbols('z'))]
            pcls = cos(sum([x[0] for x in X]))._eval_expand_trig().subs(X)
            return pcls

    def _eval_rewrite_as_sec(self, arg, **kwargs):
        return 1/sec(arg)

    def _eval_rewrite_as_csc(self, arg, **kwargs):
        return 1/sec(arg).rewrite(csc)

    def _eval_conjugate(self):
        return self.func(self.args[0].conjugate())

    def as_real_imag(self, deep=True, **hints):
        re, im = self._as_real_imag(deep=deep, **hints)
        return (cos(re)*cosh(im), -sin(re)*sinh(im))

    def _eval_expand_trig(self, **hints):
        from sympy.functions.special.polynomials import chebyshevt
        arg = self.args[0]
        x = None
        if arg.is_Add:  # TODO: Do this more efficiently for more than two terms
            x, y = arg.as_two_terms()
            sx = sin(x, evaluate=False)._eval_expand_trig()
            sy = sin(y, evaluate=False)._eval_expand_trig()
            cx = cos(x, evaluate=False)._eval_expand_trig()
            cy = cos(y, evaluate=False)._eval_expand_trig()
            return cx*cy - sx*sy
        elif arg.is_Mul:
            coeff, terms = arg.as_coeff_Mul(rational=True)
            if coeff.is_Integer:
                return chebyshevt(coeff, cos(terms))
            pi_coeff = _pi_coeff(arg)
            if pi_coeff is not None:
                if pi_coeff.is_Rational:
                    return self.rewrite(sqrt)
        return cos(arg)

    def _eval_as_leading_term(self, x, logx=None, cdir=0):
        from sympy import re
        from sympy.calculus.util import AccumBounds
        arg = self.args[0]
        x0 = arg.subs(x, 0).cancel()
        n = (x0 + S.Pi/2)/S.Pi
        if n.is_integer:
            lt = (arg - n*S.Pi + S.Pi/2).as_leading_term(x)
            return ((-1)**n)*lt
        if x0 is S.ComplexInfinity:
            x0 = arg.limit(x, 0, dir='-' if re(cdir).is_negative else '+')
        if x0 in [S.Infinity, S.NegativeInfinity]:
            return AccumBounds(-1, 1)
        return self.func(x0) if x0.is_finite else self

    def _eval_is_extended_real(self):
        if self.args[0].is_extended_real:
            return True

    def _eval_is_finite(self):
        arg = self.args[0]

        if arg.is_extended_real:
            return True

    def _eval_is_complex(self):
        if self.args[0].is_extended_real \
            or self.args[0].is_complex:
            return True


class tan(TrigonometricFunction):
    """
    The tangent function.

    Returns the tangent of x (measured in radians).

    Explanation
    ===========

    See :func:`sin` for notes about automatic evaluation.

    Examples
    ========

    >>> from sympy import tan, pi
    >>> from sympy.abc import x
    >>> tan(x**2).diff(x)
    2*x*(tan(x**2)**2 + 1)
    >>> tan(1).diff(x)
    0
    >>> tan(pi/8).expand()
    -1 + sqrt(2)

    See Also
    ========

    sin, csc, cos, sec, cot
    asin, acsc, acos, asec, atan, acot, atan2

    References
    ==========

    .. [1] https://en.wikipedia.org/wiki/Trigonometric_functions
    .. [2] http://dlmf.nist.gov/4.14
    .. [3] http://functions.wolfram.com/ElementaryFunctions/Tan

    """

    def period(self, symbol=None):
        return self._period(pi, symbol)

    def fdiff(self, argindex=1):
        if argindex == 1:
            return S.One + self**2
        else:
            raise ArgumentIndexError(self, argindex)

    def inverse(self, argindex=1):
        """
        Returns the inverse of this function.
        """
        return atan

    @classmethod
    def eval(cls, arg):
        from sympy.calculus.util import AccumBounds
        if arg.is_Number:
            if arg is S.NaN:
                return S.NaN
            elif arg.is_zero:
                return S.Zero
            elif arg is S.Infinity or arg is S.NegativeInfinity:
                return AccumBounds(S.NegativeInfinity, S.Infinity)

        if arg is S.ComplexInfinity:
            return S.NaN

        if isinstance(arg, AccumBounds):
            min, max = arg.min, arg.max
            d = floor(min/S.Pi)
            if min is not S.NegativeInfinity:
                min = min - d*S.Pi
            if max is not S.Infinity:
                max = max - d*S.Pi
            if AccumBounds(min, max).intersection(FiniteSet(S.Pi/2, S.Pi*Rational(3, 2))):
                return AccumBounds(S.NegativeInfinity, S.Infinity)
            else:
                return AccumBounds(tan(min), tan(max))

        if arg.could_extract_minus_sign():
            return -cls(-arg)

        i_coeff = arg.as_coefficient(S.ImaginaryUnit)
        if i_coeff is not None:
            return S.ImaginaryUnit*tanh(i_coeff)

        pi_coeff = _pi_coeff(arg, 2)
        if pi_coeff is not None:
            if pi_coeff.is_integer:
                return S.Zero

            if not pi_coeff.is_Rational:
                narg = pi_coeff*S.Pi
                if narg != arg:
                    return cls(narg)
                return None

            if pi_coeff.is_Rational:
                q = pi_coeff.q
                p = pi_coeff.p % q
                # ensure simplified results are returned for n*pi/5, n*pi/10
                table10 = {
                    1: sqrt(1 - 2*sqrt(5)/5),
                    2: sqrt(5 - 2*sqrt(5)),
                    3: sqrt(1 + 2*sqrt(5)/5),
                    4: sqrt(5 + 2*sqrt(5))
                    }
                if q == 5 or q == 10:
                    n = 10*p/q
                    if n > 5:
                        n = 10 - n
                        return -table10[n]
                    else:
                        return table10[n]
                if not pi_coeff.q % 2:
                    narg = pi_coeff*S.Pi*2
                    cresult, sresult = cos(narg), cos(narg - S.Pi/2)
                    if not isinstance(cresult, cos) \
                            and not isinstance(sresult, cos):
                        if sresult == 0:
                            return S.ComplexInfinity
                        return 1/sresult - cresult/sresult
                table2 = {
                    12: (3, 4),
                    20: (4, 5),
                    30: (5, 6),
                    15: (6, 10),
                    24: (6, 8),
                    40: (8, 10),
                    60: (20, 30),
                    120: (40, 60)
                    }
                if q in table2:
                    nvala, nvalb = cls(p*S.Pi/table2[q][0]), cls(p*S.Pi/table2[q][1])
                    if None == nvala or None == nvalb:
                        return None
                    return (nvala - nvalb)/(1 + nvala*nvalb)
                narg = ((pi_coeff + S.Half) % 1 - S.Half)*S.Pi
                # see cos() to specify which expressions should  be
                # expanded automatically in terms of radicals
                cresult, sresult = cos(narg), cos(narg - S.Pi/2)
                if not isinstance(cresult, cos) \
                        and not isinstance(sresult, cos):
                    if cresult == 0:
                        return S.ComplexInfinity
                    return (sresult/cresult)
                if narg != arg:
                    return cls(narg)

        if arg.is_Add:
            x, m = _peeloff_pi(arg)
            if m:
                tanm = tan(m)
                if tanm is S.ComplexInfinity:
                    return -cot(x)
                else: # tanm == 0
                    return tan(x)

        if arg.is_zero:
            return S.Zero

        if isinstance(arg, atan):
            return arg.args[0]

        if isinstance(arg, atan2):
            y, x = arg.args
            return y/x

        if isinstance(arg, asin):
            x = arg.args[0]
            return x/sqrt(1 - x**2)

        if isinstance(arg, acos):
            x = arg.args[0]
            return sqrt(1 - x**2)/x

        if isinstance(arg, acot):
            x = arg.args[0]
            return 1/x

        if isinstance(arg, acsc):
            x = arg.args[0]
            return 1/(sqrt(1 - 1/x**2)*x)

        if isinstance(arg, asec):
            x = arg.args[0]
            return sqrt(1 - 1/x**2)*x

    @staticmethod
    @cacheit
    def taylor_term(n, x, *previous_terms):
        from sympy import bernoulli
        if n < 0 or n % 2 == 0:
            return S.Zero
        else:
            x = sympify(x)

            a, b = ((n - 1)//2), 2**(n + 1)

            B = bernoulli(n + 1)
            F = factorial(n + 1)

            return (-1)**a*b*(b - 1)*B/F*x**n

    def _eval_nseries(self, x, n, logx, cdir=0):
        i = self.args[0].limit(x, 0)*2/S.Pi
        if i and i.is_Integer:
            return self.rewrite(cos)._eval_nseries(x, n=n, logx=logx)
        return Function._eval_nseries(self, x, n=n, logx=logx)

    def _eval_rewrite_as_Pow(self, arg, **kwargs):
        if isinstance(arg, log):
            I = S.ImaginaryUnit
            x = arg.args[0]
            return I*(x**-I - x**I)/(x**-I + x**I)

    def _eval_conjugate(self):
        return self.func(self.args[0].conjugate())

    def as_real_imag(self, deep=True, **hints):
        re, im = self._as_real_imag(deep=deep, **hints)
        if im:
            denom = cos(2*re) + cosh(2*im)
            return (sin(2*re)/denom, sinh(2*im)/denom)
        else:
            return (self.func(re), S.Zero)

    def _eval_expand_trig(self, **hints):
        from sympy import im, re
        arg = self.args[0]
        x = None
        if arg.is_Add:
            from sympy import symmetric_poly
            n = len(arg.args)
            TX = []
            for x in arg.args:
                tx = tan(x, evaluate=False)._eval_expand_trig()
                TX.append(tx)

            Yg = numbered_symbols('Y')
            Y = [ next(Yg) for i in range(n) ]

            p = [0, 0]
            for i in range(n + 1):
                p[1 - i % 2] += symmetric_poly(i, Y)*(-1)**((i % 4)//2)
            return (p[0]/p[1]).subs(list(zip(Y, TX)))

        elif arg.is_Mul:
            coeff, terms = arg.as_coeff_Mul(rational=True)
            if coeff.is_Integer and coeff > 1:
                I = S.ImaginaryUnit
                z = Symbol('dummy', real=True)
                P = ((1 + I*z)**coeff).expand()
                return (im(P)/re(P)).subs([(z, tan(terms))])
        return tan(arg)

    def _eval_rewrite_as_exp(self, arg, **kwargs):
        I = S.ImaginaryUnit
        if isinstance(arg, (TrigonometricFunction, HyperbolicFunction)):
            arg = arg.func(arg.args[0]).rewrite(exp)
        neg_exp, pos_exp = exp(-arg*I), exp(arg*I)
        return I*(neg_exp - pos_exp)/(neg_exp + pos_exp)

    def _eval_rewrite_as_sin(self, x, **kwargs):
        return 2*sin(x)**2/sin(2*x)

    def _eval_rewrite_as_cos(self, x, **kwargs):
        return cos(x - S.Pi/2, evaluate=False)/cos(x)

    def _eval_rewrite_as_sincos(self, arg, **kwargs):
        return sin(arg)/cos(arg)

    def _eval_rewrite_as_cot(self, arg, **kwargs):
        return 1/cot(arg)

    def _eval_rewrite_as_sec(self, arg, **kwargs):
        sin_in_sec_form = sin(arg).rewrite(sec)
        cos_in_sec_form = cos(arg).rewrite(sec)
        return sin_in_sec_form/cos_in_sec_form

    def _eval_rewrite_as_csc(self, arg, **kwargs):
        sin_in_csc_form = sin(arg).rewrite(csc)
        cos_in_csc_form = cos(arg).rewrite(csc)
        return sin_in_csc_form/cos_in_csc_form

    def _eval_rewrite_as_pow(self, arg, **kwargs):
        y = self.rewrite(cos).rewrite(pow)
        if y.has(cos):
            return None
        return y

    def _eval_rewrite_as_sqrt(self, arg, **kwargs):
        y = self.rewrite(cos).rewrite(sqrt)
        if y.has(cos):
            return None
        return y

    def _eval_as_leading_term(self, x, logx=None, cdir=0):
        arg = self.args[0]
        x0 = arg.subs(x, 0).cancel()
        n = 2*x0/S.Pi
        if n.is_integer:
            lt = (arg - n*S.Pi/2).as_leading_term(x)
            return lt if n.is_even else -1/lt
        return self.func(x0) if x0.is_finite else self

    def _eval_is_extended_real(self):
        # FIXME: currently tan(pi/2) return zoo
        return self.args[0].is_extended_real

    def _eval_is_real(self):
        arg = self.args[0]
        if arg.is_real and (arg/pi - S.Half).is_integer is False:
            return True

    def _eval_is_finite(self):
        arg = self.args[0]

        if arg.is_real and (arg/pi - S.Half).is_integer is False:
            return True

        if arg.is_imaginary:
            return True

    def _eval_is_zero(self):
        arg = self.args[0]
        if arg.is_zero:
            return True

    def _eval_is_complex(self):
        arg = self.args[0]

        if arg.is_real and (arg/pi - S.Half).is_integer is False:
            return True


class cot(TrigonometricFunction):
    """
    The cotangent function.

    Returns the cotangent of x (measured in radians).

    Explanation
    ===========

    See :func:`sin` for notes about automatic evaluation.

    Examples
    ========

    >>> from sympy import cot, pi
    >>> from sympy.abc import x
    >>> cot(x**2).diff(x)
    2*x*(-cot(x**2)**2 - 1)
    >>> cot(1).diff(x)
    0
    >>> cot(pi/12)
    sqrt(3) + 2

    See Also
    ========

    sin, csc, cos, sec, tan
    asin, acsc, acos, asec, atan, acot, atan2

    References
    ==========

    .. [1] https://en.wikipedia.org/wiki/Trigonometric_functions
    .. [2] http://dlmf.nist.gov/4.14
    .. [3] http://functions.wolfram.com/ElementaryFunctions/Cot

    """

    def period(self, symbol=None):
        return self._period(pi, symbol)

    def fdiff(self, argindex=1):
        if argindex == 1:
            return S.NegativeOne - self**2
        else:
            raise ArgumentIndexError(self, argindex)

    def inverse(self, argindex=1):
        """
        Returns the inverse of this function.
        """
        return acot

    @classmethod
    def eval(cls, arg):
        from sympy.calculus.util import AccumBounds
        if arg.is_Number:
            if arg is S.NaN:
                return S.NaN
            if arg.is_zero:
                return S.ComplexInfinity

        if arg is S.ComplexInfinity:
            return S.NaN

        if isinstance(arg, AccumBounds):
            return -tan(arg + S.Pi/2)

        if arg.could_extract_minus_sign():
            return -cls(-arg)

        i_coeff = arg.as_coefficient(S.ImaginaryUnit)
        if i_coeff is not None:
            return -S.ImaginaryUnit*coth(i_coeff)

        pi_coeff = _pi_coeff(arg, 2)
        if pi_coeff is not None:
            if pi_coeff.is_integer:
                return S.ComplexInfinity

            if not pi_coeff.is_Rational:
                narg = pi_coeff*S.Pi
                if narg != arg:
                    return cls(narg)
                return None

            if pi_coeff.is_Rational:
                if pi_coeff.q == 5 or pi_coeff.q == 10:
                    return tan(S.Pi/2 - arg)
                if pi_coeff.q > 2 and not pi_coeff.q % 2:
                    narg = pi_coeff*S.Pi*2
                    cresult, sresult = cos(narg), cos(narg - S.Pi/2)
                    if not isinstance(cresult, cos) \
                            and not isinstance(sresult, cos):
                        return 1/sresult + cresult/sresult
                table2 = {
                    12: (3, 4),
                    20: (4, 5),
                    30: (5, 6),
                    15: (6, 10),
                    24: (6, 8),
                    40: (8, 10),
                    60: (20, 30),
                    120: (40, 60)
                    }
                q = pi_coeff.q
                p = pi_coeff.p % q
                if q in table2:
                    nvala, nvalb = cls(p*S.Pi/table2[q][0]), cls(p*S.Pi/table2[q][1])
                    if None == nvala or None == nvalb:
                        return None
                    return (1 + nvala*nvalb)/(nvalb - nvala)
                narg = (((pi_coeff + S.Half) % 1) - S.Half)*S.Pi
                # see cos() to specify which expressions should be
                # expanded automatically in terms of radicals
                cresult, sresult = cos(narg), cos(narg - S.Pi/2)
                if not isinstance(cresult, cos) \
                        and not isinstance(sresult, cos):
                    if sresult == 0:
                        return S.ComplexInfinity
                    return cresult/sresult
                if narg != arg:
                    return cls(narg)

        if arg.is_Add:
            x, m = _peeloff_pi(arg)
            if m:
                cotm = cot(m)
                if cotm is S.ComplexInfinity:
                    return cot(x)
                else: # cotm == 0
                    return -tan(x)

        if arg.is_zero:
            return S.ComplexInfinity

        if isinstance(arg, acot):
            return arg.args[0]

        if isinstance(arg, atan):
            x = arg.args[0]
            return 1/x

        if isinstance(arg, atan2):
            y, x = arg.args
            return x/y

        if isinstance(arg, asin):
            x = arg.args[0]
            return sqrt(1 - x**2)/x

        if isinstance(arg, acos):
            x = arg.args[0]
            return x/sqrt(1 - x**2)

        if isinstance(arg, acsc):
            x = arg.args[0]
            return sqrt(1 - 1/x**2)*x

        if isinstance(arg, asec):
            x = arg.args[0]
            return 1/(sqrt(1 - 1/x**2)*x)

    @staticmethod
    @cacheit
    def taylor_term(n, x, *previous_terms):
        from sympy import bernoulli
        if n == 0:
            return 1/sympify(x)
        elif n < 0 or n % 2 == 0:
            return S.Zero
        else:
            x = sympify(x)

            B = bernoulli(n + 1)
            F = factorial(n + 1)

            return (-1)**((n + 1)//2)*2**(n + 1)*B/F*x**n

    def _eval_nseries(self, x, n, logx, cdir=0):
        i = self.args[0].limit(x, 0)/S.Pi
        if i and i.is_Integer:
            return self.rewrite(cos)._eval_nseries(x, n=n, logx=logx)
        return self.rewrite(tan)._eval_nseries(x, n=n, logx=logx)

    def _eval_conjugate(self):
        return self.func(self.args[0].conjugate())

    def as_real_imag(self, deep=True, **hints):
        re, im = self._as_real_imag(deep=deep, **hints)
        if im:
            denom = cos(2*re) - cosh(2*im)
            return (-sin(2*re)/denom, sinh(2*im)/denom)
        else:
            return (self.func(re), S.Zero)

    def _eval_rewrite_as_exp(self, arg, **kwargs):
        I = S.ImaginaryUnit
        if isinstance(arg, (TrigonometricFunction, HyperbolicFunction)):
            arg = arg.func(arg.args[0]).rewrite(exp)
        neg_exp, pos_exp = exp(-arg*I), exp(arg*I)
        return I*(pos_exp + neg_exp)/(pos_exp - neg_exp)

    def _eval_rewrite_as_Pow(self, arg, **kwargs):
        if isinstance(arg, log):
            I = S.ImaginaryUnit
            x = arg.args[0]
            return -I*(x**-I + x**I)/(x**-I - x**I)

    def _eval_rewrite_as_sin(self, x, **kwargs):
        return sin(2*x)/(2*(sin(x)**2))

    def _eval_rewrite_as_cos(self, x, **kwargs):
        return cos(x)/cos(x - S.Pi/2, evaluate=False)

    def _eval_rewrite_as_sincos(self, arg, **kwargs):
        return cos(arg)/sin(arg)

    def _eval_rewrite_as_tan(self, arg, **kwargs):
        return 1/tan(arg)

    def _eval_rewrite_as_sec(self, arg, **kwargs):
        cos_in_sec_form = cos(arg).rewrite(sec)
        sin_in_sec_form = sin(arg).rewrite(sec)
        return cos_in_sec_form/sin_in_sec_form

    def _eval_rewrite_as_csc(self, arg, **kwargs):
        cos_in_csc_form = cos(arg).rewrite(csc)
        sin_in_csc_form = sin(arg).rewrite(csc)
        return cos_in_csc_form/sin_in_csc_form

    def _eval_rewrite_as_pow(self, arg, **kwargs):
        y = self.rewrite(cos).rewrite(pow)
        if y.has(cos):
            return None
        return y

    def _eval_rewrite_as_sqrt(self, arg, **kwargs):
        y = self.rewrite(cos).rewrite(sqrt)
        if y.has(cos):
            return None
        return y

    def _eval_as_leading_term(self, x, logx=None, cdir=0):
        arg = self.args[0]
        x0 = arg.subs(x, 0).cancel()
        n = 2*x0/S.Pi
        if n.is_integer:
            lt = (arg - n*S.Pi/2).as_leading_term(x)
            return 1/lt if n.is_even else -lt
        return self.func(x0) if x0.is_finite else self

    def _eval_is_extended_real(self):
        return self.args[0].is_extended_real

    def _eval_expand_trig(self, **hints):
        from sympy import im, re
        arg = self.args[0]
        x = None
        if arg.is_Add:
            from sympy import symmetric_poly
            n = len(arg.args)
            CX = []
            for x in arg.args:
                cx = cot(x, evaluate=False)._eval_expand_trig()
                CX.append(cx)

            Yg = numbered_symbols('Y')
            Y = [ next(Yg) for i in range(n) ]

            p = [0, 0]
            for i in range(n, -1, -1):
                p[(n - i) % 2] += symmetric_poly(i, Y)*(-1)**(((n - i) % 4)//2)
            return (p[0]/p[1]).subs(list(zip(Y, CX)))
        elif arg.is_Mul:
            coeff, terms = arg.as_coeff_Mul(rational=True)
            if coeff.is_Integer and coeff > 1:
                I = S.ImaginaryUnit
                z = Symbol('dummy', real=True)
                P = ((z + I)**coeff).expand()
                return (re(P)/im(P)).subs([(z, cot(terms))])
        return cot(arg)  # XXX sec and csc return 1/cos and 1/sin

    def _eval_is_finite(self):
        arg = self.args[0]
        if arg.is_real and (arg/pi).is_integer is False:
            return True
        if arg.is_imaginary:
            return True

    def _eval_is_real(self):
        arg = self.args[0]
        if arg.is_real and (arg/pi).is_integer is False:
            return True

    def _eval_is_complex(self):
        arg = self.args[0]
        if arg.is_real and (arg/pi).is_integer is False:
            return True

    def _eval_subs(self, old, new):
        arg = self.args[0]
        argnew = arg.subs(old, new)
        if arg != argnew and (argnew/S.Pi).is_integer:
            return S.ComplexInfinity
        return cot(argnew)


class ReciprocalTrigonometricFunction(TrigonometricFunction):
    """Base class for reciprocal functions of trigonometric functions. """

    _reciprocal_of = None       # mandatory, to be defined in subclass
    _singularities = (S.ComplexInfinity,)

    # _is_even and _is_odd are used for correct evaluation of csc(-x), sec(-x)
    # TODO refactor into TrigonometricFunction common parts of
    # trigonometric functions eval() like even/odd, func(x+2*k*pi), etc.

    # optional, to be defined in subclasses:
    _is_even = None  # type: FuzzyBool
    _is_odd = None  # type: FuzzyBool

    @classmethod
    def eval(cls, arg):
        if arg.could_extract_minus_sign():
            if cls._is_even:
                return cls(-arg)
            if cls._is_odd:
                return -cls(-arg)

        pi_coeff = _pi_coeff(arg)
        if (pi_coeff is not None
            and not (2*pi_coeff).is_integer
            and pi_coeff.is_Rational):
                q = pi_coeff.q
                p = pi_coeff.p % (2*q)
                if p > q:
                    narg = (pi_coeff - 1)*S.Pi
                    return -cls(narg)
                if 2*p > q:
                    narg = (1 - pi_coeff)*S.Pi
                    if cls._is_odd:
                        return cls(narg)
                    elif cls._is_even:
                        return -cls(narg)

        if hasattr(arg, 'inverse') and arg.inverse() == cls:
            return arg.args[0]

        t = cls._reciprocal_of.eval(arg)
        if t is None:
            return t
        elif any(isinstance(i, cos) for i in (t, -t)):
            return (1/t).rewrite(sec)
        elif any(isinstance(i, sin) for i in (t, -t)):
            return (1/t).rewrite(csc)
        else:
            return 1/t

    def _call_reciprocal(self, method_name, *args, **kwargs):
        # Calls method_name on _reciprocal_of
        o = self._reciprocal_of(self.args[0])
        return getattr(o, method_name)(*args, **kwargs)

    def _calculate_reciprocal(self, method_name, *args, **kwargs):
        # If calling method_name on _reciprocal_of returns a value != None
        # then return the reciprocal of that value
        t = self._call_reciprocal(method_name, *args, **kwargs)
        return 1/t if t is not None else t

    def _rewrite_reciprocal(self, method_name, arg):
        # Special handling for rewrite functions. If reciprocal rewrite returns
        # unmodified expression, then return None
        t = self._call_reciprocal(method_name, arg)
        if t is not None and t != self._reciprocal_of(arg):
            return 1/t

    def _period(self, symbol):
        f = expand_mul(self.args[0])
        return self._reciprocal_of(f).period(symbol)

    def fdiff(self, argindex=1):
        return -self._calculate_reciprocal("fdiff", argindex)/self**2

    def _eval_rewrite_as_exp(self, arg, **kwargs):
        return self._rewrite_reciprocal("_eval_rewrite_as_exp", arg)

    def _eval_rewrite_as_Pow(self, arg, **kwargs):
        return self._rewrite_reciprocal("_eval_rewrite_as_Pow", arg)

    def _eval_rewrite_as_sin(self, arg, **kwargs):
        return self._rewrite_reciprocal("_eval_rewrite_as_sin", arg)

    def _eval_rewrite_as_cos(self, arg, **kwargs):
        return self._rewrite_reciprocal("_eval_rewrite_as_cos", arg)

    def _eval_rewrite_as_tan(self, arg, **kwargs):
        return self._rewrite_reciprocal("_eval_rewrite_as_tan", arg)

    def _eval_rewrite_as_pow(self, arg, **kwargs):
        return self._rewrite_reciprocal("_eval_rewrite_as_pow", arg)

    def _eval_rewrite_as_sqrt(self, arg, **kwargs):
        return self._rewrite_reciprocal("_eval_rewrite_as_sqrt", arg)

    def _eval_conjugate(self):
        return self.func(self.args[0].conjugate())

    def as_real_imag(self, deep=True, **hints):
        return (1/self._reciprocal_of(self.args[0])).as_real_imag(deep,
                                                                  **hints)

    def _eval_expand_trig(self, **hints):
        return self._calculate_reciprocal("_eval_expand_trig", **hints)

    def _eval_is_extended_real(self):
        return self._reciprocal_of(self.args[0])._eval_is_extended_real()

    def _eval_as_leading_term(self, x, logx=None, cdir=0):
        return (1/self._reciprocal_of(self.args[0]))._eval_as_leading_term(x)

    def _eval_is_finite(self):
        return (1/self._reciprocal_of(self.args[0])).is_finite

    def _eval_nseries(self, x, n, logx, cdir=0):
        return (1/self._reciprocal_of(self.args[0]))._eval_nseries(x, n, logx)


class sec(ReciprocalTrigonometricFunction):
    """
    The secant function.

    Returns the secant of x (measured in radians).

    Explanation
    ===========

    See :func:`sin` for notes about automatic evaluation.

    Examples
    ========

    >>> from sympy import sec
    >>> from sympy.abc import x
    >>> sec(x**2).diff(x)
    2*x*tan(x**2)*sec(x**2)
    >>> sec(1).diff(x)
    0

    See Also
    ========

    sin, csc, cos, tan, cot
    asin, acsc, acos, asec, atan, acot, atan2

    References
    ==========

    .. [1] https://en.wikipedia.org/wiki/Trigonometric_functions
    .. [2] http://dlmf.nist.gov/4.14
    .. [3] http://functions.wolfram.com/ElementaryFunctions/Sec

    """

    _reciprocal_of = cos
    _is_even = True

    def period(self, symbol=None):
        return self._period(symbol)

    def _eval_rewrite_as_cot(self, arg, **kwargs):
        cot_half_sq = cot(arg/2)**2
        return (cot_half_sq + 1)/(cot_half_sq - 1)

    def _eval_rewrite_as_cos(self, arg, **kwargs):
        return (1/cos(arg))

    def _eval_rewrite_as_sincos(self, arg, **kwargs):
        return sin(arg)/(cos(arg)*sin(arg))

    def _eval_rewrite_as_sin(self, arg, **kwargs):
        return (1/cos(arg).rewrite(sin))

    def _eval_rewrite_as_tan(self, arg, **kwargs):
        return (1/cos(arg).rewrite(tan))

    def _eval_rewrite_as_csc(self, arg, **kwargs):
        return csc(pi/2 - arg, evaluate=False)

    def fdiff(self, argindex=1):
        if argindex == 1:
            return tan(self.args[0])*sec(self.args[0])
        else:
            raise ArgumentIndexError(self, argindex)

    def _eval_is_complex(self):
        arg = self.args[0]

        if arg.is_complex and (arg/pi - S.Half).is_integer is False:
            return True

    @staticmethod
    @cacheit
    def taylor_term(n, x, *previous_terms):
        # Reference Formula:
        # http://functions.wolfram.com/ElementaryFunctions/Sec/06/01/02/01/
        from sympy.functions.combinatorial.numbers import euler
        if n < 0 or n % 2 == 1:
            return S.Zero
        else:
            x = sympify(x)
            k = n//2
            return (-1)**k*euler(2*k)/factorial(2*k)*x**(2*k)

    def _eval_as_leading_term(self, x, logx=None, cdir=0):
        arg = self.args[0]
        x0 = arg.subs(x, 0).cancel()
        n = (x0 + S.Pi/2)/S.Pi
        if n.is_integer:
            lt = (arg - n*S.Pi + S.Pi/2).as_leading_term(x)
            return ((-1)**n)/lt
        return self.func(x0)

class csc(ReciprocalTrigonometricFunction):
    """
    The cosecant function.

    Returns the cosecant of x (measured in radians).

    Explanation
    ===========

    See :func:`sin` for notes about automatic evaluation.

    Examples
    ========

    >>> from sympy import csc
    >>> from sympy.abc import x
    >>> csc(x**2).diff(x)
    -2*x*cot(x**2)*csc(x**2)
    >>> csc(1).diff(x)
    0

    See Also
    ========

    sin, cos, sec, tan, cot
    asin, acsc, acos, asec, atan, acot, atan2

    References
    ==========

    .. [1] https://en.wikipedia.org/wiki/Trigonometric_functions
    .. [2] http://dlmf.nist.gov/4.14
    .. [3] http://functions.wolfram.com/ElementaryFunctions/Csc

    """

    _reciprocal_of = sin
    _is_odd = True

    def period(self, symbol=None):
        return self._period(symbol)

    def _eval_rewrite_as_sin(self, arg, **kwargs):
        return (1/sin(arg))

    def _eval_rewrite_as_sincos(self, arg, **kwargs):
        return cos(arg)/(sin(arg)*cos(arg))

    def _eval_rewrite_as_cot(self, arg, **kwargs):
        cot_half = cot(arg/2)
        return (1 + cot_half**2)/(2*cot_half)

    def _eval_rewrite_as_cos(self, arg, **kwargs):
        return 1/sin(arg).rewrite(cos)

    def _eval_rewrite_as_sec(self, arg, **kwargs):
        return sec(pi/2 - arg, evaluate=False)

    def _eval_rewrite_as_tan(self, arg, **kwargs):
        return (1/sin(arg).rewrite(tan))

    def fdiff(self, argindex=1):
        if argindex == 1:
            return -cot(self.args[0])*csc(self.args[0])
        else:
            raise ArgumentIndexError(self, argindex)

    def _eval_is_complex(self):
        arg = self.args[0]
        if arg.is_real and (arg/pi).is_integer is False:
            return True

    @staticmethod
    @cacheit
    def taylor_term(n, x, *previous_terms):
        from sympy import bernoulli
        if n == 0:
            return 1/sympify(x)
        elif n < 0 or n % 2 == 0:
            return S.Zero
        else:
            x = sympify(x)
            k = n//2 + 1
            return ((-1)**(k - 1)*2*(2**(2*k - 1) - 1)*
                    bernoulli(2*k)*x**(2*k - 1)/factorial(2*k))


class sinc(Function):
    r"""
    Represents an unnormalized sinc function:

    .. math::

        \operatorname{sinc}(x) =
        \begin{cases}
          \frac{\sin x}{x} & \qquad x \neq 0 \\
          1 & \qquad x = 0
        \end{cases}

    Examples
    ========

    >>> from sympy import sinc, oo, jn
    >>> from sympy.abc import x
    >>> sinc(x)
    sinc(x)

    * Automated Evaluation

    >>> sinc(0)
    1
    >>> sinc(oo)
    0

    * Differentiation

    >>> sinc(x).diff()
    cos(x)/x - sin(x)/x**2

    * Series Expansion

    >>> sinc(x).series()
    1 - x**2/6 + x**4/120 + O(x**6)

    * As zero'th order spherical Bessel Function

    >>> sinc(x).rewrite(jn)
    jn(0, x)

    See also
    ========

    sin

    References
    ==========

    .. [1] https://en.wikipedia.org/wiki/Sinc_function

    """
    _singularities = (S.ComplexInfinity,)

    def fdiff(self, argindex=1):
        x = self.args[0]
        if argindex == 1:
            # We would like to return the Piecewise here, but Piecewise.diff
            # currently can't handle removable singularities, meaning things
            # like sinc(x).diff(x, 2) give the wrong answer at x = 0. See
            # https://github.com/sympy/sympy/issues/11402.
            #
            # return Piecewise(((x*cos(x) - sin(x))/x**2, Ne(x, S.Zero)), (S.Zero, S.true))
            return cos(x)/x - sin(x)/x**2
        else:
            raise ArgumentIndexError(self, argindex)

    @classmethod
    def eval(cls, arg):
        if arg.is_zero:
            return S.One
        if arg.is_Number:
            if arg in [S.Infinity, S.NegativeInfinity]:
                return S.Zero
            elif arg is S.NaN:
                return S.NaN

        if arg is S.ComplexInfinity:
            return S.NaN

        if arg.could_extract_minus_sign():
            return cls(-arg)

        pi_coeff = _pi_coeff(arg)
        if pi_coeff is not None:
            if pi_coeff.is_integer:
                if fuzzy_not(arg.is_zero):
                    return S.Zero
            elif (2*pi_coeff).is_integer:
                return S.NegativeOne**(pi_coeff - S.Half)/arg

    def _eval_nseries(self, x, n, logx, cdir=0):
        x = self.args[0]
        return (sin(x)/x)._eval_nseries(x, n, logx)

    def _eval_rewrite_as_jn(self, arg, **kwargs):
        from sympy.functions.special.bessel import jn
        return jn(0, arg)

    def _eval_rewrite_as_sin(self, arg, **kwargs):
        return Piecewise((sin(arg)/arg, Ne(arg, S.Zero)), (S.One, S.true))


###############################################################################
########################### TRIGONOMETRIC INVERSES ############################
###############################################################################


class InverseTrigonometricFunction(Function):
    """Base class for inverse trigonometric functions."""
    _singularities = (S.One, S.NegativeOne, S.Zero, S.ComplexInfinity)  # type: Tuple[Expr, ...]

    @staticmethod
    def _asin_table():
        # Only keys with could_extract_minus_sign() == False
        # are actually needed.
        return {
            sqrt(3)/2: S.Pi/3,
            sqrt(2)/2: S.Pi/4,
            1/sqrt(2): S.Pi/4,
            sqrt((5 - sqrt(5))/8): S.Pi/5,
            sqrt(2)*sqrt(5 - sqrt(5))/4: S.Pi/5,
            sqrt((5 + sqrt(5))/8): S.Pi*Rational(2, 5),
            sqrt(2)*sqrt(5 + sqrt(5))/4: S.Pi*Rational(2, 5),
            S.Half: S.Pi/6,
            sqrt(2 - sqrt(2))/2: S.Pi/8,
            sqrt(S.Half - sqrt(2)/4): S.Pi/8,
            sqrt(2 + sqrt(2))/2: S.Pi*Rational(3, 8),
            sqrt(S.Half + sqrt(2)/4): S.Pi*Rational(3, 8),
            (sqrt(5) - 1)/4: S.Pi/10,
            (1 - sqrt(5))/4: -S.Pi/10,
            (sqrt(5) + 1)/4: S.Pi*Rational(3, 10),
            sqrt(6)/4 - sqrt(2)/4: S.Pi/12,
            -sqrt(6)/4 + sqrt(2)/4: -S.Pi/12,
            (sqrt(3) - 1)/sqrt(8): S.Pi/12,
            (1 - sqrt(3))/sqrt(8): -S.Pi/12,
            sqrt(6)/4 + sqrt(2)/4: S.Pi*Rational(5, 12),
            (1 + sqrt(3))/sqrt(8): S.Pi*Rational(5, 12)
        }

    @staticmethod
    def _atan_table():
        # Only keys with could_extract_minus_sign() == False
        # are actually needed.
        return {
            sqrt(3)/3: S.Pi/6,
            1/sqrt(3): S.Pi/6,
            sqrt(3): S.Pi/3,
            sqrt(2) - 1: S.Pi/8,
            1 - sqrt(2): -S.Pi/8,
            1 + sqrt(2): S.Pi*Rational(3, 8),
            sqrt(5 - 2*sqrt(5)): S.Pi/5,
            sqrt(5 + 2*sqrt(5)): S.Pi*Rational(2, 5),
            sqrt(1 - 2*sqrt(5)/5): S.Pi/10,
            sqrt(1 + 2*sqrt(5)/5): S.Pi*Rational(3, 10),
            2 - sqrt(3): S.Pi/12,
            -2 + sqrt(3): -S.Pi/12,
            2 + sqrt(3): S.Pi*Rational(5, 12)
        }

    @staticmethod
    def _acsc_table():
        # Keys for which could_extract_minus_sign()
        # will obviously return True are omitted.
        return {
            2*sqrt(3)/3: S.Pi/3,
            sqrt(2): S.Pi/4,
            sqrt(2 + 2*sqrt(5)/5): S.Pi/5,
            1/sqrt(Rational(5, 8) - sqrt(5)/8): S.Pi/5,
            sqrt(2 - 2*sqrt(5)/5): S.Pi*Rational(2, 5),
            1/sqrt(Rational(5, 8) + sqrt(5)/8): S.Pi*Rational(2, 5),
            2: S.Pi/6,
            sqrt(4 + 2*sqrt(2)): S.Pi/8,
            2/sqrt(2 - sqrt(2)): S.Pi/8,
            sqrt(4 - 2*sqrt(2)): S.Pi*Rational(3, 8),
            2/sqrt(2 + sqrt(2)): S.Pi*Rational(3, 8),
            1 + sqrt(5): S.Pi/10,
            sqrt(5) - 1: S.Pi*Rational(3, 10),
            -(sqrt(5) - 1): S.Pi*Rational(-3, 10),
            sqrt(6) + sqrt(2): S.Pi/12,
            sqrt(6) - sqrt(2): S.Pi*Rational(5, 12),
            -(sqrt(6) - sqrt(2)): S.Pi*Rational(-5, 12)
        }


class asin(InverseTrigonometricFunction):
    """
    The inverse sine function.

    Returns the arcsine of x in radians.

    Explanation
    ===========

    ``asin(x)`` will evaluate automatically in the cases ``oo``, ``-oo``,
    ``0``, ``1``, ``-1`` and for some instances when the result is a rational
    multiple of pi (see the eval class method).

    A purely imaginary argument will lead to an asinh expression.

    Examples
    ========

    >>> from sympy import asin, oo
    >>> asin(1)
    pi/2
    >>> asin(-1)
    -pi/2
    >>> asin(-oo)
    oo*I
    >>> asin(oo)
    -oo*I

    See Also
    ========

    sin, csc, cos, sec, tan, cot
    acsc, acos, asec, atan, acot, atan2

    References
    ==========

    .. [1] https://en.wikipedia.org/wiki/Inverse_trigonometric_functions
    .. [2] http://dlmf.nist.gov/4.23
    .. [3] http://functions.wolfram.com/ElementaryFunctions/ArcSin

    """

    def fdiff(self, argindex=1):
        if argindex == 1:
            return 1/sqrt(1 - self.args[0]**2)
        else:
            raise ArgumentIndexError(self, argindex)

    def _eval_is_rational(self):
        s = self.func(*self.args)
        if s.func == self.func:
            if s.args[0].is_rational:
                return False
        else:
            return s.is_rational

    def _eval_is_positive(self):
        return self._eval_is_extended_real() and self.args[0].is_positive

    def _eval_is_negative(self):
        return self._eval_is_extended_real() and self.args[0].is_negative

    @classmethod
    def eval(cls, arg):
        if arg.is_Number:
            if arg is S.NaN:
                return S.NaN
            elif arg is S.Infinity:
                return S.NegativeInfinity*S.ImaginaryUnit
            elif arg is S.NegativeInfinity:
                return S.Infinity*S.ImaginaryUnit
            elif arg.is_zero:
                return S.Zero
            elif arg is S.One:
                return S.Pi/2
            elif arg is S.NegativeOne:
                return -S.Pi/2

        if arg is S.ComplexInfinity:
            return S.ComplexInfinity

        if arg.could_extract_minus_sign():
            return -cls(-arg)

        if arg.is_number:
            asin_table = cls._asin_table()
            if arg in asin_table:
                return asin_table[arg]

        i_coeff = arg.as_coefficient(S.ImaginaryUnit)
        if i_coeff is not None:
            return S.ImaginaryUnit*asinh(i_coeff)

        if arg.is_zero:
            return S.Zero

        if isinstance(arg, sin):
            ang = arg.args[0]
            if ang.is_comparable:
                ang %= 2*pi # restrict to [0,2*pi)
                if ang > pi: # restrict to (-pi,pi]
                    ang = pi - ang

                # restrict to [-pi/2,pi/2]
                if ang > pi/2:
                    ang = pi - ang
                if ang < -pi/2:
                    ang = -pi - ang

                return ang

        if isinstance(arg, cos): # acos(x) + asin(x) = pi/2
            ang = arg.args[0]
            if ang.is_comparable:
                return pi/2 - acos(arg)

    @staticmethod
    @cacheit
    def taylor_term(n, x, *previous_terms):
        if n < 0 or n % 2 == 0:
            return S.Zero
        else:
            x = sympify(x)
            if len(previous_terms) >= 2 and n > 2:
                p = previous_terms[-2]
                return p*(n - 2)**2/(n*(n - 1))*x**2
            else:
                k = (n - 1) // 2
                R = RisingFactorial(S.Half, k)
                F = factorial(k)
                return R/F*x**n/n

    def _eval_as_leading_term(self, x, logx=None, cdir=0):
        from sympy import im
        arg = self.args[0]
        x0 = arg.subs(x, 0).cancel()
        if x0.is_zero:
            return arg.as_leading_term(x)
        if x0 is S.ComplexInfinity:
            return S.ImaginaryUnit*log(arg.as_leading_term(x))
        if cdir != 0:
            cdir = arg.dir(x, cdir)
        if im(cdir) < 0 and x0.is_real and x0 < S.NegativeOne:
            return -S.Pi - self.func(x0)
        elif im(cdir) > 0 and x0.is_real and x0 > S.One:
            return S.Pi - self.func(x0)
        return self.func(x0)

    def _eval_nseries(self, x, n, logx, cdir=0): #asin
        from sympy import Dummy, im, O
        arg0 = self.args[0].subs(x, 0)
        if arg0 is S.One:
            t = Dummy('t', positive=True)
            ser = asin(S.One - t**2).rewrite(log).nseries(t, 0, 2*n)
            arg1 = S.One - self.args[0]
            f = arg1.as_leading_term(x)
            g = (arg1 - f)/ f
            if not g.is_meromorphic(x, 0):   # cannot be expanded
                return O(1) if n == 0 else S.Pi/2 + O(sqrt(x))
            res1 = sqrt(S.One + g)._eval_nseries(x, n=n, logx=logx)
            res = (res1.removeO()*sqrt(f)).expand()
            return ser.removeO().subs(t, res).expand().powsimp() + O(x**n, x)

        if arg0 is S.NegativeOne:
            t = Dummy('t', positive=True)
            ser = asin(S.NegativeOne + t**2).rewrite(log).nseries(t, 0, 2*n)
            arg1 = S.One + self.args[0]
            f = arg1.as_leading_term(x)
            g = (arg1 - f)/ f
            if not g.is_meromorphic(x, 0):   # cannot be expanded
                return O(1) if n == 0 else -S.Pi/2 + O(sqrt(x))
            res1 = sqrt(S.One + g)._eval_nseries(x, n=n, logx=logx)
            res = (res1.removeO()*sqrt(f)).expand()
            return ser.removeO().subs(t, res).expand().powsimp() + O(x**n, x)

        res = Function._eval_nseries(self, x, n=n, logx=logx)
        if arg0 is S.ComplexInfinity:
            return res
        if cdir != 0:
            cdir = self.args[0].dir(x, cdir)
        if im(cdir) < 0 and arg0.is_real and arg0 < S.NegativeOne:
            return -S.Pi - res
        elif im(cdir) > 0 and arg0.is_real and arg0 > S.One:
            return S.Pi - res
        return res

    def _eval_rewrite_as_acos(self, x, **kwargs):
        return S.Pi/2 - acos(x)

    def _eval_rewrite_as_atan(self, x, **kwargs):
        return 2*atan(x/(1 + sqrt(1 - x**2)))

    def _eval_rewrite_as_log(self, x, **kwargs):
        return -S.ImaginaryUnit*log(S.ImaginaryUnit*x + sqrt(1 - x**2))

    def _eval_rewrite_as_acot(self, arg, **kwargs):
        return 2*acot((1 + sqrt(1 - arg**2))/arg)

    def _eval_rewrite_as_asec(self, arg, **kwargs):
        return S.Pi/2 - asec(1/arg)

    def _eval_rewrite_as_acsc(self, arg, **kwargs):
        return acsc(1/arg)

    def _eval_is_extended_real(self):
        x = self.args[0]
        return x.is_extended_real and (1 - abs(x)).is_nonnegative

    def inverse(self, argindex=1):
        """
        Returns the inverse of this function.
        """
        return sin


class acos(InverseTrigonometricFunction):
    """
    The inverse cosine function.

    Returns the arc cosine of x (measured in radians).

    Examples
    ========

    ``acos(x)`` will evaluate automatically in the cases
    ``oo``, ``-oo``, ``0``, ``1``, ``-1`` and for some instances when
    the result is a rational multiple of pi (see the eval class method).

    ``acos(zoo)`` evaluates to ``zoo``
    (see note in :class:`sympy.functions.elementary.trigonometric.asec`)

    A purely imaginary argument will be rewritten to asinh.

    Examples
    ========

    >>> from sympy import acos, oo
    >>> acos(1)
    0
    >>> acos(0)
    pi/2
    >>> acos(oo)
    oo*I

    See Also
    ========

    sin, csc, cos, sec, tan, cot
    asin, acsc, asec, atan, acot, atan2

    References
    ==========

    .. [1] https://en.wikipedia.org/wiki/Inverse_trigonometric_functions
    .. [2] http://dlmf.nist.gov/4.23
    .. [3] http://functions.wolfram.com/ElementaryFunctions/ArcCos

    """

    def fdiff(self, argindex=1):
        if argindex == 1:
            return -1/sqrt(1 - self.args[0]**2)
        else:
            raise ArgumentIndexError(self, argindex)

    def _eval_is_rational(self):
        s = self.func(*self.args)
        if s.func == self.func:
            if s.args[0].is_rational:
                return False
        else:
            return s.is_rational

    @classmethod
    def eval(cls, arg):
        if arg.is_Number:
            if arg is S.NaN:
                return S.NaN
            elif arg is S.Infinity:
                return S.Infinity*S.ImaginaryUnit
            elif arg is S.NegativeInfinity:
                return S.NegativeInfinity*S.ImaginaryUnit
            elif arg.is_zero:
                return S.Pi/2
            elif arg is S.One:
                return S.Zero
            elif arg is S.NegativeOne:
                return S.Pi

        if arg is S.ComplexInfinity:
            return S.ComplexInfinity

        if arg.is_number:
            asin_table = cls._asin_table()
            if arg in asin_table:
                return pi/2 - asin_table[arg]
            elif -arg in asin_table:
                return pi/2 + asin_table[-arg]

        i_coeff = arg.as_coefficient(S.ImaginaryUnit)
        if i_coeff is not None:
            return pi/2 - asin(arg)

        if isinstance(arg, cos):
            ang = arg.args[0]
            if ang.is_comparable:
                ang %= 2*pi # restrict to [0,2*pi)
                if ang > pi: # restrict to [0,pi]
                    ang = 2*pi - ang

                return ang

        if isinstance(arg, sin): # acos(x) + asin(x) = pi/2
            ang = arg.args[0]
            if ang.is_comparable:
                return pi/2 - asin(arg)

    @staticmethod
    @cacheit
    def taylor_term(n, x, *previous_terms):
        if n == 0:
            return S.Pi/2
        elif n < 0 or n % 2 == 0:
            return S.Zero
        else:
            x = sympify(x)
            if len(previous_terms) >= 2 and n > 2:
                p = previous_terms[-2]
                return p*(n - 2)**2/(n*(n - 1))*x**2
            else:
                k = (n - 1) // 2
                R = RisingFactorial(S.Half, k)
                F = factorial(k)
                return -R/F*x**n/n

    def _eval_as_leading_term(self, x, logx=None, cdir=0):
        from sympy import im
        arg = self.args[0]
        x0 = arg.subs(x, 0).cancel()
        if x0 == 1:
            return sqrt(2)*sqrt((S.One - arg).as_leading_term(x))
        if x0 is S.ComplexInfinity:
            return S.ImaginaryUnit*log(arg.as_leading_term(x))
        if cdir != 0:
            cdir = arg.dir(x, cdir)
        if im(cdir) < 0 and x0.is_real and x0 < S.NegativeOne:
            return 2*S.Pi - self.func(x0)
        elif im(cdir) > 0 and x0.is_real and x0 > S.One:
            return -self.func(x0)
        return self.func(x0)

    def _eval_is_extended_real(self):
        x = self.args[0]
        return x.is_extended_real and (1 - abs(x)).is_nonnegative

    def _eval_is_nonnegative(self):
        return self._eval_is_extended_real()

    def _eval_nseries(self, x, n, logx, cdir=0): #acos
        from sympy import Dummy, im, O
        arg0 = self.args[0].subs(x, 0)
        if arg0 is S.One:
            t = Dummy('t', positive=True)
            ser = acos(S.One - t**2).rewrite(log).nseries(t, 0, 2*n)
            arg1 = S.One - self.args[0]
            f = arg1.as_leading_term(x)
            g = (arg1 - f)/ f
            if not g.is_meromorphic(x, 0):   # cannot be expanded
                return O(1) if n == 0 else O(sqrt(x))
            res1 = sqrt(S.One + g)._eval_nseries(x, n=n, logx=logx)
            res = (res1.removeO()*sqrt(f)).expand()
            return ser.removeO().subs(t, res).expand().powsimp() + O(x**n, x)

        if arg0 is S.NegativeOne:
            t = Dummy('t', positive=True)
            ser = acos(S.NegativeOne + t**2).rewrite(log).nseries(t, 0, 2*n)
            arg1 = S.One + self.args[0]
            f = arg1.as_leading_term(x)
            g = (arg1 - f)/ f
            if not g.is_meromorphic(x, 0):   # cannot be expanded
                return O(1) if n == 0 else S.Pi + O(sqrt(x))
            res1 = sqrt(S.One + g)._eval_nseries(x, n=n, logx=logx)
            res = (res1.removeO()*sqrt(f)).expand()
            return ser.removeO().subs(t, res).expand().powsimp() + O(x**n, x)

        res = Function._eval_nseries(self, x, n=n, logx=logx)
        if arg0 is S.ComplexInfinity:
            return res
        if cdir != 0:
            cdir = self.args[0].dir(x, cdir)
        if im(cdir) < 0 and arg0.is_real and arg0 < S.NegativeOne:
            return 2*S.Pi - res
        elif im(cdir) > 0 and arg0.is_real and arg0 > S.One:
            return -res
        return res

    def _eval_rewrite_as_log(self, x, **kwargs):
        return S.Pi/2 + S.ImaginaryUnit*\
            log(S.ImaginaryUnit*x + sqrt(1 - x**2))

    def _eval_rewrite_as_asin(self, x, **kwargs):
        return S.Pi/2 - asin(x)

    def _eval_rewrite_as_atan(self, x, **kwargs):
        return atan(sqrt(1 - x**2)/x) + (S.Pi/2)*(1 - x*sqrt(1/x**2))

    def inverse(self, argindex=1):
        """
        Returns the inverse of this function.
        """
        return cos

    def _eval_rewrite_as_acot(self, arg, **kwargs):
        return S.Pi/2 - 2*acot((1 + sqrt(1 - arg**2))/arg)

    def _eval_rewrite_as_asec(self, arg, **kwargs):
        return asec(1/arg)

    def _eval_rewrite_as_acsc(self, arg, **kwargs):
        return S.Pi/2 - acsc(1/arg)

    def _eval_conjugate(self):
        z = self.args[0]
        r = self.func(self.args[0].conjugate())
        if z.is_extended_real is False:
            return r
        elif z.is_extended_real and (z + 1).is_nonnegative and (z - 1).is_nonpositive:
            return r


class atan(InverseTrigonometricFunction):
    """
    The inverse tangent function.

    Returns the arc tangent of x (measured in radians).

    Explanation
    ===========

    ``atan(x)`` will evaluate automatically in the cases
    ``oo``, ``-oo``, ``0``, ``1``, ``-1`` and for some instances when the
    result is a rational multiple of pi (see the eval class method).

    Examples
    ========

    >>> from sympy import atan, oo
    >>> atan(0)
    0
    >>> atan(1)
    pi/4
    >>> atan(oo)
    pi/2

    See Also
    ========

    sin, csc, cos, sec, tan, cot
    asin, acsc, acos, asec, acot, atan2

    References
    ==========

    .. [1] https://en.wikipedia.org/wiki/Inverse_trigonometric_functions
    .. [2] http://dlmf.nist.gov/4.23
    .. [3] http://functions.wolfram.com/ElementaryFunctions/ArcTan

    """
    _singularities = (S.ImaginaryUnit, -S.ImaginaryUnit)

    def fdiff(self, argindex=1):
        if argindex == 1:
            return 1/(1 + self.args[0]**2)
        else:
            raise ArgumentIndexError(self, argindex)

    def _eval_is_rational(self):
        s = self.func(*self.args)
        if s.func == self.func:
            if s.args[0].is_rational:
                return False
        else:
            return s.is_rational

    def _eval_is_positive(self):
        return self.args[0].is_extended_positive

    def _eval_is_nonnegative(self):
        return self.args[0].is_extended_nonnegative

    def _eval_is_zero(self):
        return self.args[0].is_zero

    def _eval_is_real(self):
        return self.args[0].is_extended_real

    @classmethod
    def eval(cls, arg):
        if arg.is_Number:
            if arg is S.NaN:
                return S.NaN
            elif arg is S.Infinity:
                return S.Pi/2
            elif arg is S.NegativeInfinity:
                return -S.Pi/2
            elif arg.is_zero:
                return S.Zero
            elif arg is S.One:
                return S.Pi/4
            elif arg is S.NegativeOne:
                return -S.Pi/4

        if arg is S.ComplexInfinity:
            from sympy.calculus.util import AccumBounds
            return AccumBounds(-S.Pi/2, S.Pi/2)

        if arg.could_extract_minus_sign():
            return -cls(-arg)

        if arg.is_number:
            atan_table = cls._atan_table()
            if arg in atan_table:
                return atan_table[arg]

        i_coeff = arg.as_coefficient(S.ImaginaryUnit)
        if i_coeff is not None:
            return S.ImaginaryUnit*atanh(i_coeff)

        if arg.is_zero:
            return S.Zero

        if isinstance(arg, tan):
            ang = arg.args[0]
            if ang.is_comparable:
                ang %= pi # restrict to [0,pi)
                if ang > pi/2: # restrict to [-pi/2,pi/2]
                    ang -= pi

                return ang

        if isinstance(arg, cot): # atan(x) + acot(x) = pi/2
            ang = arg.args[0]
            if ang.is_comparable:
                ang = pi/2 - acot(arg)
                if ang > pi/2: # restrict to [-pi/2,pi/2]
                    ang -= pi
                return ang

    @staticmethod
    @cacheit
    def taylor_term(n, x, *previous_terms):
        if n < 0 or n % 2 == 0:
            return S.Zero
        else:
            x = sympify(x)
            return (-1)**((n - 1)//2)*x**n/n

    def _eval_as_leading_term(self, x, logx=None, cdir=0):
        from sympy import im, re
        arg = self.args[0]
        x0 = arg.subs(x, 0).cancel()
        if x0.is_zero:
            return arg.as_leading_term(x)
        if x0 is S.ComplexInfinity:
            return acot(1/arg)._eval_as_leading_term(x, cdir=cdir)
        if cdir != 0:
            cdir = arg.dir(x, cdir)
        if re(cdir) < 0 and re(x0).is_zero and im(x0) > S.One:
            return self.func(x0) - S.Pi
        elif re(cdir) > 0 and re(x0).is_zero and im(x0) < S.NegativeOne:
            return self.func(x0) + S.Pi
        return self.func(x0)

    def _eval_nseries(self, x, n, logx, cdir=0): #atan
        from sympy import im, re
        arg0 = self.args[0].subs(x, 0)
        res = Function._eval_nseries(self, x, n=n, logx=logx)
        if cdir != 0:
            cdir = self.args[0].dir(x, cdir)
        if arg0 is S.ComplexInfinity:
            if re(cdir) > 0:
                return res - S.Pi
            return res
        if re(cdir) < 0 and re(arg0).is_zero and im(arg0) > S.One:
            return res - S.Pi
        elif re(cdir) > 0 and re(arg0).is_zero and im(arg0) < S.NegativeOne:
            return res + S.Pi
        return res

    def _eval_rewrite_as_log(self, x, **kwargs):
        return S.ImaginaryUnit/2*(log(S.One - S.ImaginaryUnit*x)
            - log(S.One + S.ImaginaryUnit*x))

    def _eval_aseries(self, n, args0, x, logx):
        if args0[0] is S.Infinity:
            return (S.Pi/2 - atan(1/self.args[0]))._eval_nseries(x, n, logx)
        elif args0[0] is S.NegativeInfinity:
            return (-S.Pi/2 - atan(1/self.args[0]))._eval_nseries(x, n, logx)
        else:
            return super()._eval_aseries(n, args0, x, logx)

    def inverse(self, argindex=1):
        """
        Returns the inverse of this function.
        """
        return tan

    def _eval_rewrite_as_asin(self, arg, **kwargs):
        return sqrt(arg**2)/arg*(S.Pi/2 - asin(1/sqrt(1 + arg**2)))

    def _eval_rewrite_as_acos(self, arg, **kwargs):
        return sqrt(arg**2)/arg*acos(1/sqrt(1 + arg**2))

    def _eval_rewrite_as_acot(self, arg, **kwargs):
        return acot(1/arg)

    def _eval_rewrite_as_asec(self, arg, **kwargs):
        return sqrt(arg**2)/arg*asec(sqrt(1 + arg**2))

    def _eval_rewrite_as_acsc(self, arg, **kwargs):
        return sqrt(arg**2)/arg*(S.Pi/2 - acsc(sqrt(1 + arg**2)))


class acot(InverseTrigonometricFunction):
    r"""
    The inverse cotangent function.

    Returns the arc cotangent of x (measured in radians).

    Explanation
    ===========

    ``acot(x)`` will evaluate automatically in the cases ``oo``, ``-oo``,
    ``zoo``, ``0``, ``1``, ``-1`` and for some instances when the result is a
    rational multiple of pi (see the eval class method).

    A purely imaginary argument will lead to an ``acoth`` expression.

    ``acot(x)`` has a branch cut along `(-i, i)`, hence it is discontinuous
    at 0. Its range for real ``x`` is `(-\frac{\pi}{2}, \frac{\pi}{2}]`.

    Examples
    ========

    >>> from sympy import acot, sqrt
    >>> acot(0)
    pi/2
    >>> acot(1)
    pi/4
    >>> acot(sqrt(3) - 2)
    -5*pi/12

    See Also
    ========

    sin, csc, cos, sec, tan, cot
    asin, acsc, acos, asec, atan, atan2

    References
    ==========

    .. [1] http://dlmf.nist.gov/4.23
    .. [2] http://functions.wolfram.com/ElementaryFunctions/ArcCot

    """
    _singularities = (S.ImaginaryUnit, -S.ImaginaryUnit)

    def fdiff(self, argindex=1):
        if argindex == 1:
            return -1/(1 + self.args[0]**2)
        else:
            raise ArgumentIndexError(self, argindex)

    def _eval_is_rational(self):
        s = self.func(*self.args)
        if s.func == self.func:
            if s.args[0].is_rational:
                return False
        else:
            return s.is_rational

    def _eval_is_positive(self):
        return self.args[0].is_nonnegative

    def _eval_is_negative(self):
        return self.args[0].is_negative

    def _eval_is_extended_real(self):
        return self.args[0].is_extended_real

    @classmethod
    def eval(cls, arg):
        if arg.is_Number:
            if arg is S.NaN:
                return S.NaN
            elif arg is S.Infinity:
                return S.Zero
            elif arg is S.NegativeInfinity:
                return S.Zero
            elif arg.is_zero:
                return S.Pi/ 2
            elif arg is S.One:
                return S.Pi/4
            elif arg is S.NegativeOne:
                return -S.Pi/4

        if arg is S.ComplexInfinity:
            return S.Zero

        if arg.could_extract_minus_sign():
            return -cls(-arg)

        if arg.is_number:
            atan_table = cls._atan_table()
            if arg in atan_table:
                ang = pi/2 - atan_table[arg]
                if ang > pi/2: # restrict to (-pi/2,pi/2]
                    ang -= pi
                return ang

        i_coeff = arg.as_coefficient(S.ImaginaryUnit)
        if i_coeff is not None:
            return -S.ImaginaryUnit*acoth(i_coeff)

        if arg.is_zero:
            return S.Pi*S.Half

        if isinstance(arg, cot):
            ang = arg.args[0]
            if ang.is_comparable:
                ang %= pi # restrict to [0,pi)
                if ang > pi/2: # restrict to (-pi/2,pi/2]
                    ang -= pi;
                return ang

        if isinstance(arg, tan): # atan(x) + acot(x) = pi/2
            ang = arg.args[0]
            if ang.is_comparable:
                ang = pi/2 - atan(arg)
                if ang > pi/2: # restrict to (-pi/2,pi/2]
                    ang -= pi
                return ang

    @staticmethod
    @cacheit
    def taylor_term(n, x, *previous_terms):
        if n == 0:
            return S.Pi/2  # FIX THIS
        elif n < 0 or n % 2 == 0:
            return S.Zero
        else:
            x = sympify(x)
            return (-1)**((n + 1)//2)*x**n/n

    def _eval_as_leading_term(self, x, logx=None, cdir=0):
        from sympy import im, re
        arg = self.args[0]
        x0 = arg.subs(x, 0).cancel()
        if x0 is S.ComplexInfinity:
            return (1/arg).as_leading_term(x)
        if cdir != 0:
            cdir = arg.dir(x, cdir)
        if x0.is_zero:
            if re(cdir) < 0:
                return self.func(x0) - S.Pi
            return self.func(x0)
        if re(cdir) > 0 and re(x0).is_zero and im(x0) > S.Zero and im(x0) < S.One:
            return self.func(x0) + S.Pi
        if re(cdir) < 0 and re(x0).is_zero and im(x0) < S.Zero and im(x0) > S.NegativeOne:
            return self.func(x0) - S.Pi
        return self.func(x0)

    def _eval_nseries(self, x, n, logx, cdir=0): #acot
        from sympy import im, re
        arg0 = self.args[0].subs(x, 0)
        res = Function._eval_nseries(self, x, n=n, logx=logx)
        if arg0 is S.ComplexInfinity:
            return res
        if cdir != 0:
            cdir = self.args[0].dir(x, cdir)
        if arg0.is_zero:
            if re(cdir) < 0:
                return res - S.Pi
            return res
        if re(cdir) > 0 and re(arg0).is_zero and im(arg0) > S.Zero and im(arg0) < S.One:
            return res + S.Pi
        if re(cdir) < 0 and re(arg0).is_zero and im(arg0) < S.Zero and im(arg0) > S.NegativeOne:
            return res - S.Pi
        return res

    def _eval_aseries(self, n, args0, x, logx):
        if args0[0] is S.Infinity:
            return (S.Pi/2 - acot(1/self.args[0]))._eval_nseries(x, n, logx)
        elif args0[0] is S.NegativeInfinity:
            return (S.Pi*Rational(3, 2) - acot(1/self.args[0]))._eval_nseries(x, n, logx)
        else:
            return super(atan, self)._eval_aseries(n, args0, x, logx)

    def _eval_rewrite_as_log(self, x, **kwargs):
        return S.ImaginaryUnit/2*(log(1 - S.ImaginaryUnit/x)
            - log(1 + S.ImaginaryUnit/x))

    def inverse(self, argindex=1):
        """
        Returns the inverse of this function.
        """
        return cot

    def _eval_rewrite_as_asin(self, arg, **kwargs):
        return (arg*sqrt(1/arg**2)*
                (S.Pi/2 - asin(sqrt(-arg**2)/sqrt(-arg**2 - 1))))

    def _eval_rewrite_as_acos(self, arg, **kwargs):
        return arg*sqrt(1/arg**2)*acos(sqrt(-arg**2)/sqrt(-arg**2 - 1))

    def _eval_rewrite_as_atan(self, arg, **kwargs):
        return atan(1/arg)

    def _eval_rewrite_as_asec(self, arg, **kwargs):
        return arg*sqrt(1/arg**2)*asec(sqrt((1 + arg**2)/arg**2))

    def _eval_rewrite_as_acsc(self, arg, **kwargs):
        return arg*sqrt(1/arg**2)*(S.Pi/2 - acsc(sqrt((1 + arg**2)/arg**2)))


class asec(InverseTrigonometricFunction):
    r"""
    The inverse secant function.

    Returns the arc secant of x (measured in radians).

    Explanation
    ===========

    ``asec(x)`` will evaluate automatically in the cases ``oo``, ``-oo``,
    ``0``, ``1``, ``-1`` and for some instances when the result is a rational
    multiple of pi (see the eval class method).

    ``asec(x)`` has branch cut in the interval [-1, 1]. For complex arguments,
    it can be defined [4]_ as

    .. math::
        \operatorname{sec^{-1}}(z) = -i\frac{\log\left(\sqrt{1 - z^2} + 1\right)}{z}

    At ``x = 0``, for positive branch cut, the limit evaluates to ``zoo``. For
    negative branch cut, the limit

    .. math::
        \lim_{z \to 0}-i\frac{\log\left(-\sqrt{1 - z^2} + 1\right)}{z}

    simplifies to :math:`-i\log\left(z/2 + O\left(z^3\right)\right)` which
    ultimately evaluates to ``zoo``.

    As ``acos(x)`` = ``asec(1/x)``, a similar argument can be given for
    ``acos(x)``.

    Examples
    ========

    >>> from sympy import asec, oo
    >>> asec(1)
    0
    >>> asec(-1)
    pi
    >>> asec(0)
    zoo
    >>> asec(-oo)
    pi/2

    See Also
    ========

    sin, csc, cos, sec, tan, cot
    asin, acsc, acos, atan, acot, atan2

    References
    ==========

    .. [1] https://en.wikipedia.org/wiki/Inverse_trigonometric_functions
    .. [2] http://dlmf.nist.gov/4.23
    .. [3] http://functions.wolfram.com/ElementaryFunctions/ArcSec
    .. [4] http://reference.wolfram.com/language/ref/ArcSec.html

    """

    @classmethod
    def eval(cls, arg):
        if arg.is_zero:
            return S.ComplexInfinity
        if arg.is_Number:
            if arg is S.NaN:
                return S.NaN
            elif arg is S.One:
                return S.Zero
            elif arg is S.NegativeOne:
                return S.Pi
        if arg in [S.Infinity, S.NegativeInfinity, S.ComplexInfinity]:
            return S.Pi/2

        if arg.is_number:
            acsc_table = cls._acsc_table()
            if arg in acsc_table:
                return pi/2 - acsc_table[arg]
            elif -arg in acsc_table:
                return pi/2 + acsc_table[-arg]

        if isinstance(arg, sec):
            ang = arg.args[0]
            if ang.is_comparable:
                ang %= 2*pi # restrict to [0,2*pi)
                if ang > pi: # restrict to [0,pi]
                    ang = 2*pi - ang

                return ang

        if isinstance(arg, csc): # asec(x) + acsc(x) = pi/2
            ang = arg.args[0]
            if ang.is_comparable:
                return pi/2 - acsc(arg)

    def fdiff(self, argindex=1):
        if argindex == 1:
            return 1/(self.args[0]**2*sqrt(1 - 1/self.args[0]**2))
        else:
            raise ArgumentIndexError(self, argindex)

    def inverse(self, argindex=1):
        """
        Returns the inverse of this function.
        """
        return sec

    def _eval_as_leading_term(self, x, logx=None, cdir=0):
        from sympy import im
        arg = self.args[0]
        x0 = arg.subs(x, 0).cancel()
        if x0 == 1:
            return sqrt(2)*sqrt((arg - S.One).as_leading_term(x))
        if x0.is_zero:
            return S.ImaginaryUnit*log(arg.as_leading_term(x))
        if cdir != 0:
            cdir = arg.dir(x, cdir)
        if im(cdir) < 0 and x0.is_real and x0 > S.Zero and x0 < S.One:
            return -self.func(x0)
        elif im(cdir) > 0 and x0.is_real and x0 < S.Zero and x0 > S.NegativeOne:
            return 2*S.Pi - self.func(x0)
        return self.func(x0)

    def _eval_nseries(self, x, n, logx, cdir=0): #asec
        from sympy import Dummy, im, O
        arg0 = self.args[0].subs(x, 0)
        if arg0 is S.One:
            t = Dummy('t', positive=True)
            ser = asec(S.One + t**2).rewrite(log).nseries(t, 0, 2*n)
            arg1 = S.NegativeOne + self.args[0]
            f = arg1.as_leading_term(x)
            g = (arg1 - f)/ f
            res1 = sqrt(S.One + g)._eval_nseries(x, n=n, logx=logx)
            res = (res1.removeO()*sqrt(f)).expand()
            return ser.removeO().subs(t, res).expand().powsimp() + O(x**n, x)

        if arg0 is S.NegativeOne:
            t = Dummy('t', positive=True)
            ser = asec(S.NegativeOne - t**2).rewrite(log).nseries(t, 0, 2*n)
            arg1 = S.NegativeOne - self.args[0]
            f = arg1.as_leading_term(x)
            g = (arg1 - f)/ f
            res1 = sqrt(S.One + g)._eval_nseries(x, n=n, logx=logx)
            res = (res1.removeO()*sqrt(f)).expand()
            return ser.removeO().subs(t, res).expand().powsimp() + O(x**n, x)

        res = Function._eval_nseries(self, x, n=n, logx=logx)
        if arg0 is S.ComplexInfinity:
            return res
        if cdir != 0:
            cdir = self.args[0].dir(x, cdir)
        if im(cdir) < 0 and arg0.is_real and arg0 > S.Zero and arg0 < S.One:
            return -res
        elif im(cdir) > 0 and arg0.is_real and arg0 < S.Zero and arg0 > S.NegativeOne:
            return 2*S.Pi - res
        return res

    def _eval_is_extended_real(self):
        x = self.args[0]
        if x.is_extended_real is False:
            return False
        return fuzzy_or(((x - 1).is_nonnegative, (-x - 1).is_nonnegative))

    def _eval_rewrite_as_log(self, arg, **kwargs):
        return S.Pi/2 + S.ImaginaryUnit*log(S.ImaginaryUnit/arg + sqrt(1 - 1/arg**2))

    def _eval_rewrite_as_asin(self, arg, **kwargs):
        return S.Pi/2 - asin(1/arg)

    def _eval_rewrite_as_acos(self, arg, **kwargs):
        return acos(1/arg)

    def _eval_rewrite_as_atan(self, arg, **kwargs):
        return sqrt(arg**2)/arg*(-S.Pi/2 + 2*atan(arg + sqrt(arg**2 - 1)))

    def _eval_rewrite_as_acot(self, arg, **kwargs):
        return sqrt(arg**2)/arg*(-S.Pi/2 + 2*acot(arg - sqrt(arg**2 - 1)))

    def _eval_rewrite_as_acsc(self, arg, **kwargs):
        return S.Pi/2 - acsc(arg)


class acsc(InverseTrigonometricFunction):
    """
    The inverse cosecant function.

    Returns the arc cosecant of x (measured in radians).

    Explanation
    ===========

    ``acsc(x)`` will evaluate automatically in the cases ``oo``, ``-oo``,
    ``0``, ``1``, ``-1`` and for some instances when the result is a rational
    multiple of pi (see the eval class method).

    Examples
    ========

    >>> from sympy import acsc, oo
    >>> acsc(1)
    pi/2
    >>> acsc(-1)
    -pi/2
    >>> acsc(oo)
    0
    >>> acsc(-oo) == acsc(oo)
    True
    >>> acsc(0)
    zoo

    See Also
    ========

    sin, csc, cos, sec, tan, cot
    asin, acos, asec, atan, acot, atan2

    References
    ==========

    .. [1] https://en.wikipedia.org/wiki/Inverse_trigonometric_functions
    .. [2] http://dlmf.nist.gov/4.23
    .. [3] http://functions.wolfram.com/ElementaryFunctions/ArcCsc

    """

    @classmethod
    def eval(cls, arg):
        if arg.is_zero:
            return S.ComplexInfinity
        if arg.is_Number:
            if arg is S.NaN:
                return S.NaN
            elif arg is S.One:
                return S.Pi/2
            elif arg is S.NegativeOne:
                return -S.Pi/2
        if arg in [S.Infinity, S.NegativeInfinity, S.ComplexInfinity]:
            return S.Zero

        if arg.could_extract_minus_sign():
            return -cls(-arg)

        if arg.is_number:
            acsc_table = cls._acsc_table()
            if arg in acsc_table:
                return acsc_table[arg]

        if isinstance(arg, csc):
            ang = arg.args[0]
            if ang.is_comparable:
                ang %= 2*pi # restrict to [0,2*pi)
                if ang > pi: # restrict to (-pi,pi]
                    ang = pi - ang

                # restrict to [-pi/2,pi/2]
                if ang > pi/2:
                    ang = pi - ang
                if ang < -pi/2:
                    ang = -pi - ang

                return ang

        if isinstance(arg, sec): # asec(x) + acsc(x) = pi/2
            ang = arg.args[0]
            if ang.is_comparable:
                return pi/2 - asec(arg)

    def fdiff(self, argindex=1):
        if argindex == 1:
            return -1/(self.args[0]**2*sqrt(1 - 1/self.args[0]**2))
        else:
            raise ArgumentIndexError(self, argindex)

    def inverse(self, argindex=1):
        """
        Returns the inverse of this function.
        """
        return csc

    def _eval_as_leading_term(self, x, logx=None, cdir=0):
        from sympy import im
        arg = self.args[0]
        x0 = arg.subs(x, 0).cancel()
        if x0.is_zero:
            return S.ImaginaryUnit*log(arg.as_leading_term(x))
        if x0 is S.ComplexInfinity:
            return arg.as_leading_term(x)
        if cdir != 0:
            cdir = arg.dir(x, cdir)
        if im(cdir) < 0 and x0.is_real and x0 > S.Zero and x0 < S.One:
            return S.Pi - self.func(x0)
        elif im(cdir) > 0 and x0.is_real and x0 < S.Zero and x0 > S.NegativeOne:
            return -S.Pi - self.func(x0)
        return self.func(x0)

    def _eval_nseries(self, x, n, logx, cdir=0): #acsc
        from sympy import Dummy, im, O
        arg0 = self.args[0].subs(x, 0)
        if arg0 is S.One:
            t = Dummy('t', positive=True)
            ser = acsc(S.One + t**2).rewrite(log).nseries(t, 0, 2*n)
            arg1 = S.NegativeOne + self.args[0]
            f = arg1.as_leading_term(x)
            g = (arg1 - f)/ f
            res1 = sqrt(S.One + g)._eval_nseries(x, n=n, logx=logx)
            res = (res1.removeO()*sqrt(f)).expand()
            return ser.removeO().subs(t, res).expand().powsimp() + O(x**n, x)

        if arg0 is S.NegativeOne:
            t = Dummy('t', positive=True)
            ser = acsc(S.NegativeOne - t**2).rewrite(log).nseries(t, 0, 2*n)
            arg1 = S.NegativeOne - self.args[0]
            f = arg1.as_leading_term(x)
            g = (arg1 - f)/ f
            res1 = sqrt(S.One + g)._eval_nseries(x, n=n, logx=logx)
            res = (res1.removeO()*sqrt(f)).expand()
            return ser.removeO().subs(t, res).expand().powsimp() + O(x**n, x)

        res = Function._eval_nseries(self, x, n=n, logx=logx)
        if arg0 is S.ComplexInfinity:
            return res
        if cdir != 0:
            cdir = self.args[0].dir(x, cdir)
        if im(cdir) < 0 and arg0.is_real and arg0 > S.Zero and arg0 < S.One:
            return S.Pi - res
        elif im(cdir) > 0 and arg0.is_real and arg0 < S.Zero and arg0 > S.NegativeOne:
            return -S.Pi - res
        return res

    def _eval_rewrite_as_log(self, arg, **kwargs):
        return -S.ImaginaryUnit*log(S.ImaginaryUnit/arg + sqrt(1 - 1/arg**2))

    def _eval_rewrite_as_asin(self, arg, **kwargs):
        return asin(1/arg)

    def _eval_rewrite_as_acos(self, arg, **kwargs):
        return S.Pi/2 - acos(1/arg)

    def _eval_rewrite_as_atan(self, arg, **kwargs):
        return sqrt(arg**2)/arg*(S.Pi/2 - atan(sqrt(arg**2 - 1)))

    def _eval_rewrite_as_acot(self, arg, **kwargs):
        return sqrt(arg**2)/arg*(S.Pi/2 - acot(1/sqrt(arg**2 - 1)))

    def _eval_rewrite_as_asec(self, arg, **kwargs):
        return S.Pi/2 - asec(arg)


class atan2(InverseTrigonometricFunction):
    r"""
    The function ``atan2(y, x)`` computes `\operatorname{atan}(y/x)` taking
    two arguments `y` and `x`.  Signs of both `y` and `x` are considered to
    determine the appropriate quadrant of `\operatorname{atan}(y/x)`.
    The range is `(-\pi, \pi]`. The complete definition reads as follows:

    .. math::

        \operatorname{atan2}(y, x) =
        \begin{cases}
          \arctan\left(\frac y x\right) & \qquad x > 0 \\
          \arctan\left(\frac y x\right) + \pi& \qquad y \ge 0 , x < 0 \\
          \arctan\left(\frac y x\right) - \pi& \qquad y < 0 , x < 0 \\
          +\frac{\pi}{2} & \qquad y > 0 , x = 0 \\
          -\frac{\pi}{2} & \qquad y < 0 , x = 0 \\
          \text{undefined} & \qquad y = 0, x = 0
        \end{cases}

    Attention: Note the role reversal of both arguments. The `y`-coordinate
    is the first argument and the `x`-coordinate the second.

    If either `x` or `y` is complex:

    .. math::

        \operatorname{atan2}(y, x) =
            -i\log\left(\frac{x + iy}{\sqrt{x**2 + y**2}}\right)

    Examples
    ========

    Going counter-clock wise around the origin we find the
    following angles:

    >>> from sympy import atan2
    >>> atan2(0, 1)
    0
    >>> atan2(1, 1)
    pi/4
    >>> atan2(1, 0)
    pi/2
    >>> atan2(1, -1)
    3*pi/4
    >>> atan2(0, -1)
    pi
    >>> atan2(-1, -1)
    -3*pi/4
    >>> atan2(-1, 0)
    -pi/2
    >>> atan2(-1, 1)
    -pi/4

    which are all correct. Compare this to the results of the ordinary
    `\operatorname{atan}` function for the point `(x, y) = (-1, 1)`

    >>> from sympy import atan, S
    >>> atan(S(1)/-1)
    -pi/4
    >>> atan2(1, -1)
    3*pi/4

    where only the `\operatorname{atan2}` function reurns what we expect.
    We can differentiate the function with respect to both arguments:

    >>> from sympy import diff
    >>> from sympy.abc import x, y
    >>> diff(atan2(y, x), x)
    -y/(x**2 + y**2)

    >>> diff(atan2(y, x), y)
    x/(x**2 + y**2)

    We can express the `\operatorname{atan2}` function in terms of
    complex logarithms:

    >>> from sympy import log
    >>> atan2(y, x).rewrite(log)
    -I*log((x + I*y)/sqrt(x**2 + y**2))

    and in terms of `\operatorname(atan)`:

    >>> from sympy import atan
    >>> atan2(y, x).rewrite(atan)
    Piecewise((2*atan(y/(x + sqrt(x**2 + y**2))), Ne(y, 0)), (pi, re(x) < 0), (0, Ne(x, 0)), (nan, True))

    but note that this form is undefined on the negative real axis.

    See Also
    ========

    sin, csc, cos, sec, tan, cot
    asin, acsc, acos, asec, atan, acot

    References
    ==========

    .. [1] https://en.wikipedia.org/wiki/Inverse_trigonometric_functions
    .. [2] https://en.wikipedia.org/wiki/Atan2
    .. [3] http://functions.wolfram.com/ElementaryFunctions/ArcTan2

    """

    @classmethod
    def eval(cls, y, x):
        from sympy import Heaviside, im, re
        if x is S.NegativeInfinity:
            if y.is_zero:
                # Special case y = 0 because we define Heaviside(0) = 1/2
                return S.Pi
            return 2*S.Pi*(Heaviside(re(y))) - S.Pi
        elif x is S.Infinity:
            return S.Zero
        elif x.is_imaginary and y.is_imaginary and x.is_number and y.is_number:
            x = im(x)
            y = im(y)

        if x.is_extended_real and y.is_extended_real:
            if x.is_positive:
                return atan(y/x)
            elif x.is_negative:
                if y.is_negative:
                    return atan(y/x) - S.Pi
                elif y.is_nonnegative:
                    return atan(y/x) + S.Pi
            elif x.is_zero:
                if y.is_positive:
                    return S.Pi/2
                elif y.is_negative:
                    return -S.Pi/2
                elif y.is_zero:
                    return S.NaN
        if y.is_zero:
            if x.is_extended_nonzero:
                return S.Pi*(S.One - Heaviside(x))
            if x.is_number:
                return Piecewise((S.Pi, re(x) < 0),
                                 (0, Ne(x, 0)),
                                 (S.NaN, True))
        if x.is_number and y.is_number:
            return -S.ImaginaryUnit*log(
                (x + S.ImaginaryUnit*y)/sqrt(x**2 + y**2))

    def _eval_rewrite_as_log(self, y, x, **kwargs):
        return -S.ImaginaryUnit*log((x + S.ImaginaryUnit*y)/sqrt(x**2 + y**2))

    def _eval_rewrite_as_atan(self, y, x, **kwargs):
        from sympy import re
        return Piecewise((2*atan(y/(x + sqrt(x**2 + y**2))), Ne(y, 0)),
                         (pi, re(x) < 0),
                         (0, Ne(x, 0)),
                         (S.NaN, True))

    def _eval_rewrite_as_arg(self, y, x, **kwargs):
        from sympy import arg
        if x.is_extended_real and y.is_extended_real:
            return arg(x + y*S.ImaginaryUnit)
        n = x + S.ImaginaryUnit*y
        d = x**2 + y**2
        return arg(n/sqrt(d)) - S.ImaginaryUnit*log(abs(n)/sqrt(abs(d)))

    def _eval_is_extended_real(self):
        return self.args[0].is_extended_real and self.args[1].is_extended_real

    def _eval_conjugate(self):
        return self.func(self.args[0].conjugate(), self.args[1].conjugate())

    def fdiff(self, argindex):
        y, x = self.args
        if argindex == 1:
            # Diff wrt y
            return x/(x**2 + y**2)
        elif argindex == 2:
            # Diff wrt x
            return -y/(x**2 + y**2)
        else:
            raise ArgumentIndexError(self, argindex)

    def _eval_evalf(self, prec):
        y, x = self.args
        if x.is_extended_real and y.is_extended_real:
            return super()._eval_evalf(prec)
