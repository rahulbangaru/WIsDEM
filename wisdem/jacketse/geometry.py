import numpy as np

# Set up inputs
r_foot = 20.0
r_head = 10.0
n_legs = 4
n_bays = 3  # n_x
L = 50.0  # total height of the jacket
q = 1.0  # ratio of bay heights, assumed to be constant

l_osg = 0.0
l_tp = 0.0

# Do calculations to get the rough topology
xi = r_head / r_foot  # must be <= 1.
nu = 2 * np.pi / n_legs  # angle enclosed by two legs
psi_s = np.arctan(r_foot * (1 - xi) / L)  # spatial batter angle
psi_p = np.arctan(r_foot * (1 - xi) * np.sin(nu / 2.0) / L)

tmp = q ** np.arange(n_bays)
bay_heights = l_i = (L - l_osg - l_tp) / (np.sum(tmp) / tmp)
# TODO : add test to verify np.sum(bay_heights == L)

lower_bay_heights = np.hstack((0.0, bay_heights[:-1]))
lower_bay_radii = r_i = r_foot - np.tan(psi_s) * (l_osg + np.cumsum(lower_bay_heights))

# x joint layer info
l_mi = l_i[:-1] * r_i[:-1] / (r_i[:-1] + r_i[1:])
# r_mi = r_foot - np.tan(psi_s) * (l_osg + np.cumsum(lower_bay_heights) + l_mi)  # I don't think we actually use this value later
# print(r_mi)


# Take in member properties, like diameters and thicknesses


# Determine member cross-sectional properties
