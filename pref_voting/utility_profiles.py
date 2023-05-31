'''
    File: utility_profiles.py
    Author: Eric Pacuit (epacuit@umd.edu)
    Date: May 26, 2023
    
    Functions to reason about profiles of utilities.
'''


from math import ceil
import numpy as np
import networkx as nx
from tabulate import tabulate
from tabulate import  SEPARATING_LINE
from pref_voting.profiles_with_ties import ProfileWithTies
from pref_voting.rankings import Ranking

# turn off future warnings.
# getting the following warning when calling tabulate to display a profile: 
# /Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8/site-packages/tabulate.py:1027: FutureWarning: elementwise comparison failed; returning scalar instead, but in the future will perform elementwise comparison
#  if headers == "keys" and not rows:
# see https://stackoverflow.com/questions/40659212/futurewarning-elementwise-comparison-failed-returning-scalar-but-in-the-futur
#
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

# #######
# Utility function
# #######


class Utility(object):
    """
    A utility function. A utility function is a map from a set of alternatives to the real numbers.  The domain of the utility function is the set of alternatives.

    :param utils: Dictionary in which the keys are the alternatives and the values are the utilities.
    :type utils: dict[int or str: float]
    :param cmap: Dictionary mapping the alternatives (keys of the ``utils``) to candidate names (strings).  If not provided, each alternative is mapped to itself.
    :type cmap: dict[int or str: str], optional
    :param domain: The domain of the utility function. If not provided, the domain is the set of keys of the ``utils`` dictionary.
    """
    def __init__(self, utils, domain=None, cmap=None):
        """Constructor method for the Utility class."""

        assert domain is None or all([x in domain for x in utils.keys()]), f"The domain {domain} must contain all elements is the utility map {utils}"
        
        self.utils = utils
        self.domain = list(utils.keys()) if domain is None else domain
        self.cmap = {x:str(x) for x in self.domain} if cmap is None else cmap

    def val(self, x): 
        """
        Returns the utility of ``x``.
        """
        assert x in self.domain, f"{x} must be in the domain"
        return self.utils[x] if x in self.utils.keys() else None
    
    def items_with_util(self, u):
        """Returns a list of the items that are assigned the utility ``u``."""
        return [x for x in self.utils.keys() if self.utils[x] == u]

    def has_utility(self, x): 
        """Returns True if x has a utility."""
        return x in self.utils.keys()
    
    def strict_pref(self, x, y):
        """Returns True if ``x`` is strictly preferred to ``y``.

        The return value is True when both ``x`` and ``y`` are assigned utilities and the utility of ``x`` is strictly greater than the utility of ``y``.
        """
        return (self.has_utility(x) and self.has_utility(y)) and self.utils[x] > self.utils[y]

    def indiff(self, x, y):
        """Returns True if ``x`` is indifferent with ``y``.

        The return value is True when both ``x`` and ``y`` are assigned utilities and the utility of ``x`` equals the utility of ``y``.
        """
        return (self.has_utility(x) and self.has_utility(y)) and self.utils[x] == self.utils[y]

    def weak_pref(self, x, y):
        """Returns True if ``x`` is weakly preferred to ``y``.

        The return value is True when both ``x`` and ``y`` are assigned utilities and the utility of ``x`` is at least as  greater than the utility of ``y``.
        """

        return self.strict_pref(x, y) or self.indiff(x, y)

    def remove_cand(self, x):
        """Returns a utility with the item ``x`` removed."""

        new_utils = {y: self.utils[y] for y in self.utils.keys() if y != x}
        new_domain = [y for y in self.domain if y != x]
        new_cmap = {y: self.cmap[y] for y in self.cmap.keys() if y != x}
        return Utility(new_utils, domain=new_domain, cmap=new_cmap)
    
    def ranking(self): 
        """Return the ranking generated by this utility function."""
        
        sorted_utils = sorted(list(set(self.utils.values())), reverse=True)
        return Ranking(
            {x:u_idx + 1 for u_idx, u in enumerate(sorted_utils) 
             for x in self.utils.keys() if self.utils[x] == u})

    def has_tie(self): 
        """Return True when the utility has a tie."""
        return self.ranking().has_ties()

    def is_linear(self, num_cands):
        """Return True when the utility is a linear order of ``num_cands`` candidates. 
        """

        return self.ranking().is_linear(num_cands=num_cands)

    def represents_ranking(self, r): 
        """Return True when the utility represents the ranking ``r``."""
        for x in r.cands: 
            if x not in self.utils.keys():
                return False
        for x in r.cands: 
            for y in r.cands: 
                if r.strict_pref(x, y) and not self.strict_pref(x, y): 
                    return False
                elif r.indiff(x, y) and not self.indiff(x, y): 
                    return False
                
        return True
    
    def transformation(self, func): 
        """
        Return a new utility function that is the transformation of this utility function by the function ``func``.        
        """
        return Utility({
            x: func(x) for x in self.utils.keys()
        }, domain = self.domain, cmap=self.cmap)
    
    def linear_transformation(self, a=1, b=0): 
        """Return a linear transformation of the utility function: ``a * u(x) + b``.
        """
        
        lin_func = lambda x: a * self.utils[x] + b
        return self.transformation(lin_func)
    
    def normalize(self): 
        """Return a normalized utility function.  Applies the *Kaplan* normalization to the utility function: 
        The new utility of an element x of the domain is (u(x) - min({u(x) | x in the domain})) / (max({u(x) | x in the domain })).
        """

        max_util = max(self.utils.values())
        min_util = min(self.utils.values())
        
        if max_util == min_util: 
            return Utility({x: 0 for x in self.utils.keys()}, domain = self.domain)
        else: 
            return Utility({
                x: (self.utils[x] - min_util) / (max_util - min_util) for x in self.utils.keys()
            }, domain = self.domain)

    def expectation(self, prob):
        """Return the expected utility given a probability distribution ``prob``."""

        assert all([x in self.domain for x in prob.keys()]), "The domain of the probability distribution must be a subset of the domain of the utility function."

        return sum([prob[x] * self.util(x) for x in self.domain if x in prob.keys() and self.has_utility(x)])

    def __call__(self, x): 
        """
        Returns the utility of ``x``.
        """
        assert x in self.domain, f"{x} must be in the domain."
        return self.utils[x] if x in self.utils.keys() else None
    
    def __str__(self):
        """
        Display the utility as a string.
        """
        u_str = ""
        for x in self.domain:
            if x in self.utils.keys(): 
                u_str += f"U({self.cmap[x]}) = {self.utils[x]}" + ("; " if x != self.domain[-1] else "")
            else: 
                u_str += f"{self.cmap[x]} is not assigned a utility" + ("; " if x != self.domain[-1] else "")
                
        return u_str


class UtilityProfile(object):
    """An anonymous profile of (truncated) utilities.  

    :param utilities: List of utilities in the profile, where a utility is either a :class:`Utility` object or a dictionary.
    :type utilities: list[dict[int or str: float]] or list[Utility]
    :param ucounts: List of the number of voters associated with each utility.  Should be the same length as utilities.  If not provided, it is assumed that 1 voters submitted each element of ``utilities``.
    :type ucounts: list[int], optional
    :param domain: List of alternatives in the profile.  If not provided, it is the alternatives that are assigned a utility by least on voter.
    :type domain: list[int] or list[str], optional
    :param cmap: Dictionary mapping alternatives to alternative names (strings).  If not provided, each alternative name is mapped to itself.
    :type cmap: dict[int or str: str], optional

    :Example:

    The following code creates a profile in which
    2 voters submitted the ranking 0 ranked first, 1 ranked second, and 2 ranked third; 3 voters submitted the ranking 1 and 2 are tied for first place and 0 is ranked second; and 1 voter submitted the ranking in which 2 is ranked first and 0 is ranked second:

    .. code-block:: python

        uprof =  UtilityProfile([{"x":1, "y":3, "z":1}, {"x":0, "y":-1, "z":4}, {"x":0.5, "y":-1}, {"x":0, "y":1, "z":2}], ucounts=[2, 3, 1, 1], domain=["x", "y", "z"], cmap={0:"x", 1:"y", 2:"z"})

    """

    def __init__(self, utilities, ucounts=None, domain=None, cmap=None):
        """Constructor method"""

        assert ucounts is None or len(utilities) == len(
            ucounts
        ), "The number of utilities much be the same as the number of ucounts"

        self.domain = (
            sorted(domain)
            if domain is not None
            else sorted(list(set([x for u in utilities for x in u.keys()])))
        )
        """The domain of the profile. """

        self.cmap = cmap if cmap is not None else {c: str(c) for c in self.domain}
        """The candidate map is a dictionary associating an alternative with the name used when displaying a alternative."""

        self._utilities = [
            Utility(u, domain = self.domain, cmap=self.cmap)
            if type(u) == dict
            else Utility(u.utils, domain=self.domain, cmap=self.cmap)
            for u in utilities
        ]
        """The list of utilities in the Profile (each utility is a :class:`Utility` object). 
        """

        self.ucounts = [1] * len(utilities) if ucounts is None else list(ucounts)

        self.num_voters = np.sum(self.ucounts)
        """The number of voters in the profile. """

    @property
    def utilities_counts(self):
        """Returns the utilities and the counts of each utility."""

        return self._utilities, self.ucounts
    
    @property
    def utilities(self):
        """Return all of the utilities in the profile."""
        
        us = list()
        for u,c in zip(self._utilities, self.ucounts): 
            us += [u] * c
        return us


    def normalize(self): 
        """Return a profile in which each utility is normalized."""
        
        return UtilityProfile([
            u.normalize() for u in self._utilities
        ], ucounts = self.ucounts, domain = self.domain, cmap=self.cmap)
    
    def has_utility(self, x):
        """Return True if ``x`` is assigned a utility by at least one voter."""

        return any([u.has_utility(x) for u in self._utilities])

    def util_sum(self, x): 
        """Return the sum of the utilities of ``x``.  If ``x`` is not assigned a utility by any voter, return None."""

        return np.sum([u(x) * c for u,c in zip(*self.utilities_counts) if u.has_utility(x)]) if self.has_utility(x) else None
    
    def util_avg(self, x): 
        """Return the sum of the utilities of ``x``.  If ``x`` is not assigned a utility by any voter, return None."""

        return np.average([u(x) * c for u,c in zip(*self.utilities_counts) if u.has_utility(x)]) if self.has_utility(x) else None
    
    def util_max(self, x): 
        """Return the maximum of the utilities of ``x``.  If ``x`` is not assigned a utility by any voter, return None."""

        return max([u(x)  for u in self._utilities if u.has_utility(x)]) if self.has_utility(x) else None
    
    def util_min(self, x): 
        """Return the minimum of the utilities of ``x``.  If ``x`` is not assigned a utility by any voter, return None."""

        return min([u(x)  for u in self._utilities if u.has_utility(x)]) if self.has_utility(x) else None

    def sum_utility_function(self):
        """Return the sum utility function of the profile."""

        return Utility(
            {
                x: self.util_sum(x)
                for x in self.domain
            },
            domain=self.domain,
        )
    def avg_utility_function(self):
        """Return the average utility function of the profile."""

        return Utility(
            {
                x: self.util_sum(x) / len(self.domain)
                for x in self.domain
            },
            domain=self.domain,
        )
    
    def to_ranking_profile(self): 
        """Return a ranking profile (a :class:ProfileWithTies) corresponding to the profile."""

        return ProfileWithTies(
            [u.ranking() for u in self._utilities],
            rcounts = self.ucounts,
            candidates = self.domain, 
            cmap = self.cmap
        )
    
    def write(self):
        """Write the profile to a string."""

        uprof_str = f"{len(self.domain)};{self.num_voters}"
        for u in self.utilities: 
            u_str = ''
            for c in u.domain: 
                if u.has_utility(c):
                    u_str += f"{c}:{u(c)},"
            uprof_str += f";{u_str[0:-1]}"
        return str(uprof_str)

    @classmethod
    def from_string(cls, uprof_str): 
        """
        Returns a profile of utilities described by ``uprof_str``.

        ``uprof_str`` must be in the format produced by the :meth:`pref_voting.UtilityProfile.write` function.
        """
        uprof_data = uprof_str.split(";")

        num_alternatives,num_voters,utilities = int(uprof_data[0]),int(uprof_data[1]),uprof_data[2:]

        util_maps = [{int(cu.split(":")[0]): float(cu.split(":")[1]) for cu in utils.split(",")} if utils != '' else {} for utils in utilities]

        if len(util_maps) != num_voters: 
            raise Exception("Number of voters does not match the number of utilities.")
        
        return cls(util_maps, domain=range(num_alternatives))

    def display(self, vmap = None, show_totals=False):
        """Display a utility profile as an ascii table (using tabulate). If ``show_totals`` is true then the sum, min, and max of the utilities are displayed.

        """
        
        utilities = self.utilities
        
        vmap = vmap if vmap is not None else {vidx: str(vidx + 1) for vidx in range(len(utilities))}
        voters = range(len(utilities))
        
        if show_totals: 
            tbl ={"Voter" : [vmap[v] for v in voters] + [SEPARATING_LINE] + ["Sum", "Min", "Max"]}
            tbl.update({self.cmap(x): [utilities[v](x) for v in voters] + [SEPARATING_LINE] + [self.util_sum(x), self.util_min(x), self.util_max(x)] for x in self.domain})
        else: 
            tbl ={"Voter" : [vmap[v] for v in voters]}
            tbl.update({str(x): [utilities[v](x) for v in voters] for x in self.domain})
        print( tabulate(tbl, headers="keys"))

