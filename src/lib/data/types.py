import numpy as np

type DimKey = str
type SubdataKey = str
type VarKey = SubdataKey | DimKey

type SpeciesKey = str

type Bounds = tuple[float, float]
type Coords = np.ndarray
