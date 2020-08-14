# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import random
from typing import Union, Optional

import torch
from torchsde._brownian_lib import BrownianTree as _BrownianTree  # noqa

from .._core.settings import LEVY_AREA_APPROXIMATIONS

from .._brownian import utils  # noqa
from .._brownian import base_brownian  # noqa


class BrownianTree(base_brownian. BaseBrownian):
    """Brownian tree with fixed entropy.

    Trades in speed for memory.

    To use:
    >>> bm = BrownianTree(t0=0.0, w0=torch.zeros(4, 1))
    >>> bm(0.5)
    tensor([[ 0.0733],
            [-0.5692],
            [ 0.1872],
            [-0.3889]])
    """

    # TODO: add support for Levy area approximation
    levy_area_approximation = 'none'

    def __init__(self,
                 t0: Union[float, torch.Tensor],
                 w0: torch.Tensor,
                 t1: Optional[Union[float, torch.Tensor]] = None,
                 w1: Optional[torch.Tensor] = None,
                 entropy: Optional[int] = None,
                 tol: float = 1e-6,
                 cache_depth: int = 9,
                 safety: Optional[float] = None,
                 levy_area_approximation: str = None,
                 **kwargs):  # noqa
        super(BrownianTree, self).__init__(**kwargs)
        if not utils.is_scalar(t0):
            raise ValueError('Initial time t0 should be a float or 0-d torch.Tensor.')

        if t1 is None:
            t1 = t0 + 1.0
        if not utils.is_scalar(t1):
            raise ValueError('Terminal time t1 should be a float or 0-d torch.Tensor.')
        if t0 > t1:
            raise ValueError(f'Initial time {t0} should be less than terminal time {t1}.')

        if levy_area_approximation != LEVY_AREA_APPROXIMATIONS.none:
            raise ValueError("Only BrownianInterval currently supports levy_area_approximation for values other than "
                             "'none'.")

        t0, t1 = float(t0), float(t1)

        if safety is None:
            safety = 0.1 * (t1 - t0)

        if entropy is None:
            entropy = random.randint(0, 2 ** 31 - 1)

        self._t0 = t0
        self._t1 = t1
        if w1 is None:
            self._bm = _BrownianTree(
                t0=t0,
                w0=w0,
                t1=t1,
                entropy=entropy,
                tol=tol,
                cache_depth=cache_depth,
                safety=safety
            )
        else:
            # This constructor is used for testing.
            self._bm = _BrownianTree(
                t0=t0,
                w0=w0,
                t1=t1,
                w1=w1,
                entropy=entropy,
                tol=tol,
                cache_depth=cache_depth,
                safety=safety
            )

        self.entropy = entropy
        self.tol = tol
        self.cache_depth = cache_depth
        self.safety = safety
        self.levy_area_approximation = levy_area_approximation

    def __call__(self, ta, tb=None):
        if tb is None:
            return self.call(ta)
        return self.call(tb) - self.call(ta)

    def call(self, t):
        return self._bm(t)

    def __repr__(self):
        return repr(self._bm)

    def to(self, *args, **kwargs):
        cache, cache_prev, cache_post = self._bm.get_cache()
        for c in (cache, cache_prev, cache_post):
            for k, v in c.items():
                c[k] = v.to(*args, **kwargs)
        seeds = self._bm.get_seeds()

        self._bm = _BrownianTree(
            entropy=self.entropy,
            tol=self.tol,
            cache_depth=self.cache_depth,
            safety=self.safety,
            cache=cache,
            cache_prev=cache_prev,
            cache_post=cache_post,
            seeds=seeds
        )

    @property
    def dtype(self):
        return self._bm.get_w0().dtype

    @property
    def device(self):
        return self._bm.get_w0().device

    @property
    def shape(self):
        return self._bm.get_w0().shape

    def get_cache(self):
        return self._bm.get_cache()

    def get_seeds(self):
        return self._bm.get_seeds()
