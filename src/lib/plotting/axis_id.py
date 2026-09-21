from typing import Literal

type AxIdXY = Literal["x", "y"]
type AxIdPolar = Literal["r"]
type AxId = AxIdXY | AxIdPolar
