"""Ito scene entry points; render settings are supplied through the Manim CLI."""

from tasteforge.media.manim_geo import Basket as GeometryBasket
from tasteforge.media.manim_geo import MarketWeb as GeometryMarketWeb
from tasteforge.media.manim_geo import SacredGeo as GeometrySacredGeo


class SacredGeo(GeometrySacredGeo):
    pass


class Basket(GeometryBasket):
    pass


class MarketWeb(GeometryMarketWeb):
    seed = 42
