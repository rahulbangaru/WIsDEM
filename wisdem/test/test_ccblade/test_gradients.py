"""
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import unittest
from os import path
from math import pi

import numpy as np
from wisdem.ccblade.ccblade import CCBlade, CCAirfoil


class TestGradients(unittest.TestCase):
    def setUp(self):

        # geometry
        self.Rhub = 1.5
        self.Rtip = 63.0

        self.r = np.array(
            [
                2.8667,
                5.6000,
                8.3333,
                11.7500,
                15.8500,
                19.9500,
                24.0500,
                28.1500,
                32.2500,
                36.3500,
                40.4500,
                44.5500,
                48.6500,
                52.7500,
                56.1667,
                58.9000,
                61.6333,
            ]
        )
        self.chord = np.array(
            [
                3.542,
                3.854,
                4.167,
                4.557,
                4.652,
                4.458,
                4.249,
                4.007,
                3.748,
                3.502,
                3.256,
                3.010,
                2.764,
                2.518,
                2.313,
                2.086,
                1.419,
            ]
        )
        self.theta = np.array(
            [
                13.308,
                13.308,
                13.308,
                13.308,
                11.480,
                10.162,
                9.011,
                7.795,
                6.544,
                5.361,
                4.188,
                3.125,
                2.319,
                1.526,
                0.863,
                0.370,
                0.106,
            ]
        )
        self.B = 3  # number of blades

        # atmosphere
        self.rho = 1.225
        self.mu = 1.81206e-5

        afinit = CCAirfoil.initFromAerodynFile  # just for shorthand
        basepath = path.join(path.dirname(path.realpath(__file__)), "../../../examples/_airfoil_files/")

        # load all airfoils
        airfoil_types = [0] * 8
        airfoil_types[0] = afinit(basepath + "Cylinder1.dat")
        airfoil_types[1] = afinit(basepath + "Cylinder2.dat")
        airfoil_types[2] = afinit(basepath + "DU40_A17.dat")
        airfoil_types[3] = afinit(basepath + "DU35_A17.dat")
        airfoil_types[4] = afinit(basepath + "DU30_A17.dat")
        airfoil_types[5] = afinit(basepath + "DU25_A17.dat")
        airfoil_types[6] = afinit(basepath + "DU21_A17.dat")
        airfoil_types[7] = afinit(basepath + "NACA64_A17.dat")

        # place at appropriate radial stations
        af_idx = [0, 0, 1, 2, 3, 3, 4, 5, 5, 6, 6, 7, 7, 7, 7, 7, 7]

        self.af = [0] * len(self.r)
        for i in range(len(self.r)):
            self.af[i] = airfoil_types[af_idx[i]]

        self.tilt = -5.0
        self.precone = 2.5
        self.yaw = 0.0
        self.shearExp = 0.2
        self.hubHt = 80.0
        self.nSector = 8

        # create CCBlade object
        self.rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=True,
        )

        # set conditions
        self.Uinf = 10.0
        tsr = 7.55
        self.pitch = 0.0
        self.Omega = self.Uinf * tsr / self.Rtip * 30.0 / pi  # convert to RPM
        self.azimuth = 90

        loads, derivs = self.rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        self.Np = loads["Np"]
        self.Tp = loads["Tp"]
        self.dNp = derivs["dNp"]
        self.dTp = derivs["dTp"]

        outputs, derivs = self.rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
        self.P, self.T, self.Q, self.M = [outputs[k] for k in ("P", "T", "Q", "M")]
        self.dP, self.dT, self.dQ, self.dM = [derivs[k] for k in ("dP", "dT", "dQ", "dM")]

        outputs, derivs = self.rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
        self.CP, self.CT, self.CQ, self.CM = [outputs[k] for k in ("CP", "CT", "CQ", "CM")]
        self.dCP, self.dCT, self.dCQ, self.dCM = [derivs[k] for k in ("dCP", "dCT", "dCQ", "dCM")]

        self.rotor.derivatives = False
        self.n = len(self.r)
        self.npts = 1  # len(Uinf)

    def test_dr1(self):

        dNp_dr = self.dNp["dr"]
        dTp_dr = self.dTp["dr"]
        dNp_dr_fd = np.zeros((self.n, self.n))
        dTp_dr_fd = np.zeros((self.n, self.n))

        for i in range(self.n):
            r = np.array(self.r)
            delta = 1e-6 * r[i]
            r[i] += delta

            rotor = CCBlade(
                r,
                self.chord,
                self.theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                self.precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
            )

            loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
            Npd = loads["Np"]
            Tpd = loads["Tp"]

            dNp_dr_fd[:, i] = (Npd - self.Np) / delta
            dTp_dr_fd[:, i] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dr_fd, dNp_dr, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dTp_dr_fd, dTp_dr, rtol=1e-4, atol=1e-8)

    def test_dr2(self):

        dT_dr = self.dT["dr"]
        dQ_dr = self.dQ["dr"]
        dM_dr = self.dM["dr"]
        dP_dr = self.dP["dr"]
        dT_dr_fd = np.zeros((self.npts, self.n))
        dQ_dr_fd = np.zeros((self.npts, self.n))
        dM_dr_fd = np.zeros((self.npts, self.n))
        dP_dr_fd = np.zeros((self.npts, self.n))

        for i in range(self.n):
            r = np.array(self.r)
            delta = 1e-6 * r[i]
            r[i] += delta

            rotor = CCBlade(
                r,
                self.chord,
                self.theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                self.precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
            )

            outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
            Pd = outputs["P"]
            Td = outputs["T"]
            Qd = outputs["Q"]
            Md = outputs["M"]

            dT_dr_fd[:, i] = (Td - self.T) / delta
            dQ_dr_fd[:, i] = (Qd - self.Q) / delta
            dM_dr_fd[:, i] = (Md - self.M) / delta
            dP_dr_fd[:, i] = (Pd - self.P) / delta

        np.testing.assert_allclose(dT_dr_fd, dT_dr, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dQ_dr_fd, dQ_dr, rtol=3e-4, atol=1e-8)
        np.testing.assert_allclose(dM_dr_fd, dM_dr, rtol=3e-4, atol=1e-8)
        np.testing.assert_allclose(dP_dr_fd, dP_dr, rtol=3e-4, atol=1e-8)

    def test_dr3(self):

        dCT_dr = self.dCT["dr"]
        dCQ_dr = self.dCQ["dr"]
        dCM_dr = self.dCM["dr"]
        dCP_dr = self.dCP["dr"]
        dCT_dr_fd = np.zeros((self.npts, self.n))
        dCQ_dr_fd = np.zeros((self.npts, self.n))
        dCM_dr_fd = np.zeros((self.npts, self.n))
        dCP_dr_fd = np.zeros((self.npts, self.n))

        for i in range(self.n):
            r = np.array(self.r)
            delta = 1e-6 * r[i]
            r[i] += delta

            rotor = CCBlade(
                r,
                self.chord,
                self.theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                self.precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
            )

            outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
            CPd = outputs["CP"]
            CTd = outputs["CT"]
            CQd = outputs["CQ"]
            CMd = outputs["CM"]

            dCT_dr_fd[:, i] = (CTd - self.CT) / delta
            dCQ_dr_fd[:, i] = (CQd - self.CQ) / delta
            dCM_dr_fd[:, i] = (CMd - self.CM) / delta
            dCP_dr_fd[:, i] = (CPd - self.CP) / delta

        np.testing.assert_allclose(dCT_dr_fd, dCT_dr, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCQ_dr_fd, dCQ_dr, rtol=3e-4, atol=1e-8)
        np.testing.assert_allclose(dCM_dr_fd, dCM_dr, rtol=3e-4, atol=1e-8)
        np.testing.assert_allclose(dCP_dr_fd, dCP_dr, rtol=3e-4, atol=1e-8)

    def test_dchord1(self):

        dNp_dchord = self.dNp["dchord"]
        dTp_dchord = self.dTp["dchord"]
        dNp_dchord_fd = np.zeros((self.n, self.n))
        dTp_dchord_fd = np.zeros((self.n, self.n))

        for i in range(self.n):
            chord = np.array(self.chord)
            delta = 1e-6 * chord[i]
            chord[i] += delta

            rotor = CCBlade(
                self.r,
                chord,
                self.theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                self.precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
            )

            loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
            Npd = loads["Np"]
            Tpd = loads["Tp"]

            dNp_dchord_fd[:, i] = (Npd - self.Np) / delta
            dTp_dchord_fd[:, i] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dchord_fd, dNp_dchord, rtol=1e-6, atol=1e-8)
        np.testing.assert_allclose(dTp_dchord_fd, dTp_dchord, rtol=5e-5, atol=1e-8)

    def test_dchord2(self):

        dT_dchord = self.dT["dchord"]
        dQ_dchord = self.dQ["dchord"]
        dM_dchord = self.dM["dchord"]
        dP_dchord = self.dP["dchord"]
        dT_dchord_fd = np.zeros((self.npts, self.n))
        dQ_dchord_fd = np.zeros((self.npts, self.n))
        dM_dchord_fd = np.zeros((self.npts, self.n))
        dP_dchord_fd = np.zeros((self.npts, self.n))

        for i in range(self.n):
            chord = np.array(self.chord)
            delta = 1e-6 * chord[i]
            chord[i] += delta

            rotor = CCBlade(
                self.r,
                chord,
                self.theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                self.precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
            )

            outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
            Pd = outputs["P"]
            Td = outputs["T"]
            Qd = outputs["Q"]
            Md = outputs["M"]

            dT_dchord_fd[:, i] = (Td - self.T) / delta
            dQ_dchord_fd[:, i] = (Qd - self.Q) / delta
            dM_dchord_fd[:, i] = (Md - self.M) / delta
            dP_dchord_fd[:, i] = (Pd - self.P) / delta

        np.testing.assert_allclose(dT_dchord_fd, dT_dchord, rtol=5e-6, atol=1e-8)
        np.testing.assert_allclose(dQ_dchord_fd, dQ_dchord, rtol=7e-5, atol=1e-8)
        np.testing.assert_allclose(dM_dchord_fd, dM_dchord, rtol=7e-5, atol=1e-8)
        np.testing.assert_allclose(dP_dchord_fd, dP_dchord, rtol=7e-5, atol=1e-8)

    def test_dchord3(self):

        dCT_dchord = self.dCT["dchord"]
        dCQ_dchord = self.dCQ["dchord"]
        dCM_dchord = self.dCM["dchord"]
        dCP_dchord = self.dCP["dchord"]
        dCT_dchord_fd = np.zeros((self.npts, self.n))
        dCQ_dchord_fd = np.zeros((self.npts, self.n))
        dCM_dchord_fd = np.zeros((self.npts, self.n))
        dCP_dchord_fd = np.zeros((self.npts, self.n))

        for i in range(self.n):
            chord = np.array(self.chord)
            delta = 1e-6 * chord[i]
            chord[i] += delta

            rotor = CCBlade(
                self.r,
                chord,
                self.theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                self.precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
            )

            outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
            CPd = outputs["CP"]
            CTd = outputs["CT"]
            CQd = outputs["CQ"]
            CMd = outputs["CM"]

            dCT_dchord_fd[:, i] = (CTd - self.CT) / delta
            dCQ_dchord_fd[:, i] = (CQd - self.CQ) / delta
            dCM_dchord_fd[:, i] = (CMd - self.CM) / delta
            dCP_dchord_fd[:, i] = (CPd - self.CP) / delta

        np.testing.assert_allclose(dCT_dchord_fd, dCT_dchord, rtol=5e-6, atol=1e-8)
        np.testing.assert_allclose(dCQ_dchord_fd, dCQ_dchord, rtol=7e-5, atol=1e-8)
        np.testing.assert_allclose(dCM_dchord_fd, dCM_dchord, rtol=7e-5, atol=1e-8)
        np.testing.assert_allclose(dCP_dchord_fd, dCP_dchord, rtol=7e-5, atol=1e-8)

    def test_dtheta1(self):

        dNp_dtheta = self.dNp["dtheta"]
        dTp_dtheta = self.dTp["dtheta"]
        dNp_dtheta_fd = np.zeros((self.n, self.n))
        dTp_dtheta_fd = np.zeros((self.n, self.n))

        for i in range(self.n):
            theta = np.array(self.theta)
            delta = 1e-6 * theta[i]
            theta[i] += delta

            rotor = CCBlade(
                self.r,
                self.chord,
                theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                self.precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
            )

            loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
            Npd = loads["Np"]
            Tpd = loads["Tp"]

            dNp_dtheta_fd[:, i] = (Npd - self.Np) / delta
            dTp_dtheta_fd[:, i] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dtheta_fd, dNp_dtheta, rtol=1e-6, atol=1e-8)
        np.testing.assert_allclose(dTp_dtheta_fd, dTp_dtheta, rtol=1e-4, atol=1e-8)

    def test_dtheta2(self):

        dT_dtheta = self.dT["dtheta"]
        dQ_dtheta = self.dQ["dtheta"]
        dM_dtheta = self.dM["dtheta"]
        dP_dtheta = self.dP["dtheta"]
        dT_dtheta_fd = np.zeros((self.npts, self.n))
        dQ_dtheta_fd = np.zeros((self.npts, self.n))
        dM_dtheta_fd = np.zeros((self.npts, self.n))
        dP_dtheta_fd = np.zeros((self.npts, self.n))

        for i in range(self.n):
            theta = np.array(self.theta)
            delta = 1e-6 * theta[i]
            theta[i] += delta

            rotor = CCBlade(
                self.r,
                self.chord,
                theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                self.precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
            )

            outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
            Pd = outputs["P"]
            Td = outputs["T"]
            Qd = outputs["Q"]
            Md = outputs["M"]

            dT_dtheta_fd[:, i] = (Td - self.T) / delta
            dQ_dtheta_fd[:, i] = (Qd - self.Q) / delta
            dM_dtheta_fd[:, i] = (Md - self.M) / delta
            dP_dtheta_fd[:, i] = (Pd - self.P) / delta

        np.testing.assert_allclose(dT_dtheta_fd, dT_dtheta, rtol=7e-5, atol=1e-8)
        np.testing.assert_allclose(dQ_dtheta_fd, dQ_dtheta, rtol=7e-5, atol=1e-8)
        np.testing.assert_allclose(dM_dtheta_fd, dM_dtheta, rtol=7e-5, atol=1e-8)
        np.testing.assert_allclose(dP_dtheta_fd, dP_dtheta, rtol=7e-5, atol=1e-8)

    def test_dtheta3(self):

        dCT_dtheta = self.dCT["dtheta"]
        dCQ_dtheta = self.dCQ["dtheta"]
        dCM_dtheta = self.dCM["dtheta"]
        dCP_dtheta = self.dCP["dtheta"]
        dCT_dtheta_fd = np.zeros((self.npts, self.n))
        dCQ_dtheta_fd = np.zeros((self.npts, self.n))
        dCM_dtheta_fd = np.zeros((self.npts, self.n))
        dCP_dtheta_fd = np.zeros((self.npts, self.n))

        for i in range(self.n):
            theta = np.array(self.theta)
            delta = 1e-6 * theta[i]
            theta[i] += delta

            rotor = CCBlade(
                self.r,
                self.chord,
                theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                self.precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
            )

            outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
            CPd = outputs["CP"]
            CTd = outputs["CT"]
            CQd = outputs["CQ"]
            CMd = outputs["CM"]

            dCT_dtheta_fd[:, i] = (CTd - self.CT) / delta
            dCQ_dtheta_fd[:, i] = (CQd - self.CQ) / delta
            dCM_dtheta_fd[:, i] = (CMd - self.CM) / delta
            dCP_dtheta_fd[:, i] = (CPd - self.CP) / delta

        np.testing.assert_allclose(dCT_dtheta_fd, dCT_dtheta, rtol=5e-6, atol=1e-8)
        np.testing.assert_allclose(dCQ_dtheta_fd, dCQ_dtheta, rtol=7e-5, atol=1e-8)
        np.testing.assert_allclose(dCM_dtheta_fd, dCM_dtheta, rtol=7e-5, atol=1e-8)
        np.testing.assert_allclose(dCP_dtheta_fd, dCP_dtheta, rtol=7e-5, atol=1e-8)

    def test_dRhub1(self):

        dNp_dRhub = self.dNp["dRhub"]
        dTp_dRhub = self.dTp["dRhub"]

        dNp_dRhub_fd = np.zeros((self.n, 1))
        dTp_dRhub_fd = np.zeros((self.n, 1))

        Rhub = float(self.Rhub)
        delta = 1e-6 * Rhub
        Rhub += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]

        dNp_dRhub_fd[:, 0] = (Npd - self.Np) / delta
        dTp_dRhub_fd[:, 0] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dRhub_fd, dNp_dRhub, rtol=1e-5, atol=1e-6)
        np.testing.assert_allclose(dTp_dRhub_fd, dTp_dRhub, rtol=1e-4, atol=1e-6)

    def test_dRhub2(self):

        dT_dRhub = self.dT["dRhub"]
        dQ_dRhub = self.dQ["dRhub"]
        dM_dRhub = self.dM["dRhub"]
        dP_dRhub = self.dP["dRhub"]

        dT_dRhub_fd = np.zeros((self.npts, 1))
        dQ_dRhub_fd = np.zeros((self.npts, 1))
        dM_dRhub_fd = np.zeros((self.npts, 1))
        dP_dRhub_fd = np.zeros((self.npts, 1))

        Rhub = float(self.Rhub)
        delta = 1e-6 * Rhub
        Rhub += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
        Pd = outputs["P"]
        Td = outputs["T"]
        Qd = outputs["Q"]
        Md = outputs["M"]

        dT_dRhub_fd[:, 0] = (Td - self.T) / delta
        dQ_dRhub_fd[:, 0] = (Qd - self.Q) / delta
        dM_dRhub_fd[:, 0] = (Md - self.M) / delta
        dP_dRhub_fd[:, 0] = (Pd - self.P) / delta

        np.testing.assert_allclose(dT_dRhub_fd, dT_dRhub, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dQ_dRhub_fd, dQ_dRhub, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dM_dRhub_fd, dM_dRhub, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dP_dRhub_fd, dP_dRhub, rtol=5e-5, atol=1e-8)

    def test_dRhub3(self):

        dCT_dRhub = self.dCT["dRhub"]
        dCQ_dRhub = self.dCQ["dRhub"]
        dCM_dRhub = self.dCM["dRhub"]
        dCP_dRhub = self.dCP["dRhub"]

        dCT_dRhub_fd = np.zeros((self.npts, 1))
        dCQ_dRhub_fd = np.zeros((self.npts, 1))
        dCM_dRhub_fd = np.zeros((self.npts, 1))
        dCP_dRhub_fd = np.zeros((self.npts, 1))

        Rhub = float(self.Rhub)
        delta = 1e-6 * Rhub
        Rhub += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
        CPd = outputs["CP"]
        CTd = outputs["CT"]
        CQd = outputs["CQ"]
        CMd = outputs["CM"]

        dCT_dRhub_fd[:, 0] = (CTd - self.CT) / delta
        dCQ_dRhub_fd[:, 0] = (CQd - self.CQ) / delta
        dCM_dRhub_fd[:, 0] = (CMd - self.CM) / delta
        dCP_dRhub_fd[:, 0] = (CPd - self.CP) / delta

        np.testing.assert_allclose(dCT_dRhub_fd, dCT_dRhub, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dCQ_dRhub_fd, dCQ_dRhub, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCM_dRhub_fd, dCM_dRhub, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCP_dRhub_fd, dCP_dRhub, rtol=5e-5, atol=1e-8)

    def test_dRtip1(self):

        dNp_dRtip = self.dNp["dRtip"]
        dTp_dRtip = self.dTp["dRtip"]

        dNp_dRtip_fd = np.zeros((self.n, 1))
        dTp_dRtip_fd = np.zeros((self.n, 1))

        Rtip = float(self.Rtip)
        delta = 1e-6 * Rtip
        Rtip += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]

        dNp_dRtip_fd[:, 0] = (Npd - self.Np) / delta
        dTp_dRtip_fd[:, 0] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dRtip_fd, dNp_dRtip, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dTp_dRtip_fd, dTp_dRtip, rtol=1e-4, atol=1e-8)

    def test_dRtip2(self):

        dT_dRtip = self.dT["dRtip"]
        dQ_dRtip = self.dQ["dRtip"]
        dM_dRtip = self.dM["dRtip"]
        dP_dRtip = self.dP["dRtip"]

        dT_dRtip_fd = np.zeros((self.npts, 1))
        dQ_dRtip_fd = np.zeros((self.npts, 1))
        dM_dRtip_fd = np.zeros((self.npts, 1))
        dP_dRtip_fd = np.zeros((self.npts, 1))

        Rtip = float(self.Rtip)
        delta = 1e-6 * Rtip
        Rtip += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
        Pd = outputs["P"]
        Td = outputs["T"]
        Qd = outputs["Q"]
        Md = outputs["M"]

        dT_dRtip_fd[:, 0] = (Td - self.T) / delta
        dQ_dRtip_fd[:, 0] = (Qd - self.Q) / delta
        dM_dRtip_fd[:, 0] = (Md - self.M) / delta
        dP_dRtip_fd[:, 0] = (Pd - self.P) / delta

        np.testing.assert_allclose(dT_dRtip_fd, dT_dRtip, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dQ_dRtip_fd, dQ_dRtip, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dM_dRtip_fd, dM_dRtip, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dP_dRtip_fd, dP_dRtip, rtol=5e-5, atol=1e-8)

    def test_dRtip3(self):

        dCT_dRtip = self.dCT["dRtip"]
        dCQ_dRtip = self.dCQ["dRtip"]
        dCM_dRtip = self.dCM["dRtip"]
        dCP_dRtip = self.dCP["dRtip"]

        dCT_dRtip_fd = np.zeros((self.npts, 1))
        dCQ_dRtip_fd = np.zeros((self.npts, 1))
        dCM_dRtip_fd = np.zeros((self.npts, 1))
        dCP_dRtip_fd = np.zeros((self.npts, 1))

        Rtip = float(self.Rtip)
        delta = 1e-6 * Rtip
        Rtip += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
        CPd = outputs["CP"]
        CTd = outputs["CT"]
        CQd = outputs["CQ"]
        CMd = outputs["CM"]

        dCT_dRtip_fd[:, 0] = (CTd - self.CT) / delta
        dCQ_dRtip_fd[:, 0] = (CQd - self.CQ) / delta
        dCM_dRtip_fd[:, 0] = (CMd - self.CM) / delta
        dCP_dRtip_fd[:, 0] = (CPd - self.CP) / delta

        np.testing.assert_allclose(dCT_dRtip_fd, dCT_dRtip, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dCQ_dRtip_fd, dCQ_dRtip, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCM_dRtip_fd, dCM_dRtip, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCP_dRtip_fd, dCP_dRtip, rtol=5e-5, atol=1e-8)

    def test_dprecone1(self):

        dNp_dprecone = self.dNp["dprecone"]
        dTp_dprecone = self.dTp["dprecone"]

        dNp_dprecone_fd = np.zeros((self.n, 1))
        dTp_dprecone_fd = np.zeros((self.n, 1))

        precone = float(self.precone)
        delta = 1e-6 * precone
        precone += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]

        dNp_dprecone_fd[:, 0] = (Npd - self.Np) / delta
        dTp_dprecone_fd[:, 0] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dprecone_fd, dNp_dprecone, rtol=1e-5, atol=1e-7)
        np.testing.assert_allclose(dTp_dprecone_fd, dTp_dprecone, rtol=1e-5, atol=1e-7)

    def test_dprecone2(self):

        dT_dprecone = self.dT["dprecone"]
        dQ_dprecone = self.dQ["dprecone"]
        dM_dprecone = self.dM["dprecone"]
        dP_dprecone = self.dP["dprecone"]

        dT_dprecone_fd = np.zeros((self.npts, 1))
        dQ_dprecone_fd = np.zeros((self.npts, 1))
        dM_dprecone_fd = np.zeros((self.npts, 1))
        dP_dprecone_fd = np.zeros((self.npts, 1))

        precone = float(self.precone)
        delta = 1e-6 * precone
        precone += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
        Pd = outputs["P"]
        Td = outputs["T"]
        Qd = outputs["Q"]
        Md = outputs["M"]

        dT_dprecone_fd[:, 0] = (Td - self.T) / delta
        dQ_dprecone_fd[:, 0] = (Qd - self.Q) / delta
        dM_dprecone_fd[:, 0] = (Md - self.M) / delta
        dP_dprecone_fd[:, 0] = (Pd - self.P) / delta

        np.testing.assert_allclose(dT_dprecone_fd, dT_dprecone, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dQ_dprecone_fd, dQ_dprecone, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dM_dprecone_fd, dM_dprecone, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dP_dprecone_fd, dP_dprecone, rtol=5e-5, atol=1e-8)

    def test_dprecone3(self):

        dCT_dprecone = self.dCT["dprecone"]
        dCQ_dprecone = self.dCQ["dprecone"]
        dCM_dprecone = self.dCM["dprecone"]
        dCP_dprecone = self.dCP["dprecone"]

        dCT_dprecone_fd = np.zeros((self.npts, 1))
        dCQ_dprecone_fd = np.zeros((self.npts, 1))
        dCM_dprecone_fd = np.zeros((self.npts, 1))
        dCP_dprecone_fd = np.zeros((self.npts, 1))

        precone = float(self.precone)
        delta = 1e-6 * precone
        precone += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
        CPd = outputs["CP"]
        CTd = outputs["CT"]
        CQd = outputs["CQ"]
        CMd = outputs["CM"]

        dCT_dprecone_fd[:, 0] = (CTd - self.CT) / delta
        dCQ_dprecone_fd[:, 0] = (CQd - self.CQ) / delta
        dCM_dprecone_fd[:, 0] = (CMd - self.CM) / delta
        dCP_dprecone_fd[:, 0] = (CPd - self.CP) / delta

        np.testing.assert_allclose(dCT_dprecone_fd, dCT_dprecone, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dCQ_dprecone_fd, dCQ_dprecone, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCM_dprecone_fd, dCM_dprecone, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCP_dprecone_fd, dCP_dprecone, rtol=5e-5, atol=1e-8)

    def test_dtilt1(self):

        dNp_dtilt = self.dNp["dtilt"]
        dTp_dtilt = self.dTp["dtilt"]

        dNp_dtilt_fd = np.zeros((self.n, 1))
        dTp_dtilt_fd = np.zeros((self.n, 1))

        tilt = float(self.tilt)
        delta = 1e-6 * tilt
        tilt += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]

        dNp_dtilt_fd[:, 0] = (Npd - self.Np) / delta
        dTp_dtilt_fd[:, 0] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dtilt_fd, dNp_dtilt, rtol=1e-6, atol=1e-8)
        np.testing.assert_allclose(dTp_dtilt_fd, dTp_dtilt, rtol=1e-5, atol=1e-8)

    def test_dtilt2(self):

        dT_dtilt = self.dT["dtilt"]
        dQ_dtilt = self.dQ["dtilt"]
        dM_dtilt = self.dM["dtilt"]
        dP_dtilt = self.dP["dtilt"]

        dT_dtilt_fd = np.zeros((self.npts, 1))
        dQ_dtilt_fd = np.zeros((self.npts, 1))
        dM_dtilt_fd = np.zeros((self.npts, 1))
        dP_dtilt_fd = np.zeros((self.npts, 1))

        tilt = float(self.tilt)
        delta = 1e-6 * tilt
        tilt += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
        Pd = outputs["P"]
        Td = outputs["T"]
        Qd = outputs["Q"]
        Md = outputs["M"]

        dT_dtilt_fd[:, 0] = (Td - self.T) / delta
        dQ_dtilt_fd[:, 0] = (Qd - self.Q) / delta
        dM_dtilt_fd[:, 0] = (Md - self.M) / delta
        dP_dtilt_fd[:, 0] = (Pd - self.P) / delta

        np.testing.assert_allclose(dT_dtilt_fd, dT_dtilt, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dQ_dtilt_fd, dQ_dtilt, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dM_dtilt_fd, dM_dtilt, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dP_dtilt_fd, dP_dtilt, rtol=5e-5, atol=1e-8)

    def test_dtilt3(self):

        dCT_dtilt = self.dCT["dtilt"]
        dCQ_dtilt = self.dCQ["dtilt"]
        dCM_dtilt = self.dCM["dtilt"]
        dCP_dtilt = self.dCP["dtilt"]

        dCT_dtilt_fd = np.zeros((self.npts, 1))
        dCQ_dtilt_fd = np.zeros((self.npts, 1))
        dCM_dtilt_fd = np.zeros((self.npts, 1))
        dCP_dtilt_fd = np.zeros((self.npts, 1))

        tilt = float(self.tilt)
        delta = 1e-6 * tilt
        tilt += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
        CPd = outputs["CP"]
        CTd = outputs["CT"]
        CQd = outputs["CQ"]
        CMd = outputs["CM"]

        dCT_dtilt_fd[:, 0] = (CTd - self.CT) / delta
        dCQ_dtilt_fd[:, 0] = (CQd - self.CQ) / delta
        dCM_dtilt_fd[:, 0] = (CMd - self.CM) / delta
        dCP_dtilt_fd[:, 0] = (CPd - self.CP) / delta

        np.testing.assert_allclose(dCT_dtilt_fd, dCT_dtilt, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dCQ_dtilt_fd, dCQ_dtilt, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCM_dtilt_fd, dCM_dtilt, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCP_dtilt_fd, dCP_dtilt, rtol=5e-5, atol=1e-8)

    def test_dhubht1(self):

        dNp_dhubht = self.dNp["dhubHt"]
        dTp_dhubht = self.dTp["dhubHt"]

        dNp_dhubht_fd = np.zeros((self.n, 1))
        dTp_dhubht_fd = np.zeros((self.n, 1))

        hubht = float(self.hubHt)
        delta = 1e-6 * hubht
        hubht += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            hubht,
            self.nSector,
            derivatives=False,
        )

        loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]

        dNp_dhubht_fd[:, 0] = (Npd - self.Np) / delta
        dTp_dhubht_fd[:, 0] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dhubht_fd, dNp_dhubht, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dTp_dhubht_fd, dTp_dhubht, rtol=1e-5, atol=1e-8)

    def test_dhubht2(self):

        dT_dhubht = self.dT["dhubHt"]
        dQ_dhubht = self.dQ["dhubHt"]
        dM_dhubht = self.dM["dhubHt"]
        dP_dhubht = self.dP["dhubHt"]

        dT_dhubht_fd = np.zeros((self.npts, 1))
        dQ_dhubht_fd = np.zeros((self.npts, 1))
        dM_dhubht_fd = np.zeros((self.npts, 1))
        dP_dhubht_fd = np.zeros((self.npts, 1))

        hubht = float(self.hubHt)
        delta = 1e-6 * hubht
        hubht += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            hubht,
            self.nSector,
            derivatives=False,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
        Pd = outputs["P"]
        Td = outputs["T"]
        Qd = outputs["Q"]
        Md = outputs["M"]

        dT_dhubht_fd[:, 0] = (Td - self.T) / delta
        dQ_dhubht_fd[:, 0] = (Qd - self.Q) / delta
        dM_dhubht_fd[:, 0] = (Md - self.M) / delta
        dP_dhubht_fd[:, 0] = (Pd - self.P) / delta

        np.testing.assert_allclose(dT_dhubht_fd, dT_dhubht, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dQ_dhubht_fd, dQ_dhubht, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dM_dhubht_fd, dM_dhubht, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dP_dhubht_fd, dP_dhubht, rtol=5e-5, atol=1e-8)

    def test_dhubht3(self):

        dCT_dhubht = self.dCT["dhubHt"]
        dCQ_dhubht = self.dCQ["dhubHt"]
        dCM_dhubht = self.dCM["dhubHt"]
        dCP_dhubht = self.dCP["dhubHt"]

        dCT_dhubht_fd = np.zeros((self.npts, 1))
        dCQ_dhubht_fd = np.zeros((self.npts, 1))
        dCM_dhubht_fd = np.zeros((self.npts, 1))
        dCP_dhubht_fd = np.zeros((self.npts, 1))

        hubht = float(self.hubHt)
        delta = 1e-6 * hubht
        hubht += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            hubht,
            self.nSector,
            derivatives=False,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
        CPd = outputs["CP"]
        CTd = outputs["CT"]
        CQd = outputs["CQ"]
        CMd = outputs["CM"]

        dCT_dhubht_fd[:, 0] = (CTd - self.CT) / delta
        dCQ_dhubht_fd[:, 0] = (CQd - self.CQ) / delta
        dCM_dhubht_fd[:, 0] = (CMd - self.CM) / delta
        dCP_dhubht_fd[:, 0] = (CPd - self.CP) / delta

        np.testing.assert_allclose(dCT_dhubht_fd, dCT_dhubht, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dCQ_dhubht_fd, dCQ_dhubht, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCM_dhubht_fd, dCM_dhubht, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCP_dhubht_fd, dCP_dhubht, rtol=5e-5, atol=1e-8)

    def test_dyaw1(self):

        dNp_dyaw = self.dNp["dyaw"]
        dTp_dyaw = self.dTp["dyaw"]

        dNp_dyaw_fd = np.zeros((self.n, 1))
        dTp_dyaw_fd = np.zeros((self.n, 1))

        yaw = float(self.yaw)
        delta = 1e-6
        yaw += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]

        dNp_dyaw_fd[:, 0] = (Npd - self.Np) / delta
        dTp_dyaw_fd[:, 0] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dyaw_fd, dNp_dyaw, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dTp_dyaw_fd, dTp_dyaw, rtol=1e-5, atol=1e-8)

    def test_dyaw2(self):

        dT_dyaw = self.dT["dyaw"]
        dQ_dyaw = self.dQ["dyaw"]
        dM_dyaw = self.dM["dyaw"]
        dP_dyaw = self.dP["dyaw"]

        dT_dyaw_fd = np.zeros((self.npts, 1))
        dQ_dyaw_fd = np.zeros((self.npts, 1))
        dM_dyaw_fd = np.zeros((self.npts, 1))
        dP_dyaw_fd = np.zeros((self.npts, 1))

        yaw = float(self.yaw)
        delta = 1e-6
        yaw += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
        Pd = outputs["P"]
        Td = outputs["T"]
        Qd = outputs["Q"]
        Md = outputs["M"]

        dT_dyaw_fd[:, 0] = (Td - self.T) / delta
        dQ_dyaw_fd[:, 0] = (Qd - self.Q) / delta
        dM_dyaw_fd[:, 0] = (Md - self.M) / delta
        dP_dyaw_fd[:, 0] = (Pd - self.P) / delta

        np.testing.assert_allclose(dT_dyaw_fd, dT_dyaw, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dQ_dyaw_fd, dQ_dyaw, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dM_dyaw_fd, dM_dyaw, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dP_dyaw_fd, dP_dyaw, rtol=5e-5, atol=1e-8)

    def test_dyaw3(self):

        dCT_dyaw = self.dCT["dyaw"]
        dCQ_dyaw = self.dCQ["dyaw"]
        dCM_dyaw = self.dCM["dyaw"]
        dCP_dyaw = self.dCP["dyaw"]

        dCT_dyaw_fd = np.zeros((self.npts, 1))
        dCQ_dyaw_fd = np.zeros((self.npts, 1))
        dCM_dyaw_fd = np.zeros((self.npts, 1))
        dCP_dyaw_fd = np.zeros((self.npts, 1))

        yaw = float(self.yaw)
        delta = 1e-6
        yaw += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
        CPd = outputs["CP"]
        CTd = outputs["CT"]
        CQd = outputs["CQ"]
        CMd = outputs["CM"]

        dCT_dyaw_fd[:, 0] = (CTd - self.CT) / delta
        dCQ_dyaw_fd[:, 0] = (CQd - self.CQ) / delta
        dCM_dyaw_fd[:, 0] = (CMd - self.CM) / delta
        dCP_dyaw_fd[:, 0] = (CPd - self.CP) / delta

        np.testing.assert_allclose(dCT_dyaw_fd, dCT_dyaw, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dCQ_dyaw_fd, dCQ_dyaw, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCM_dyaw_fd, dCM_dyaw, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCP_dyaw_fd, dCP_dyaw, rtol=5e-5, atol=1e-8)

    def test_dshear1(self):

        dNp_dshear = self.dNp["dshear"]
        dTp_dshear = self.dTp["dshear"]

        dNp_dshear_fd = np.zeros((self.n, 1))
        dTp_dshear_fd = np.zeros((self.n, 1))

        shearExp = float(self.shearExp)
        delta = 1e-6
        shearExp += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]

        dNp_dshear_fd[:, 0] = (Npd - self.Np) / delta
        dTp_dshear_fd[:, 0] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dshear_fd, dNp_dshear, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dTp_dshear_fd, dTp_dshear, rtol=1e-5, atol=1e-8)

    def test_dshear2(self):

        dT_dshear = self.dT["dshear"]
        dQ_dshear = self.dQ["dshear"]
        dM_dshear = self.dM["dshear"]
        dP_dshear = self.dP["dshear"]

        dT_dshear_fd = np.zeros((self.npts, 1))
        dQ_dshear_fd = np.zeros((self.npts, 1))
        dM_dshear_fd = np.zeros((self.npts, 1))
        dP_dshear_fd = np.zeros((self.npts, 1))

        shearExp = float(self.shearExp)
        delta = 1e-6
        shearExp += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
        Pd = outputs["P"]
        Td = outputs["T"]
        Qd = outputs["Q"]
        Md = outputs["M"]

        dT_dshear_fd[:, 0] = (Td - self.T) / delta
        dQ_dshear_fd[:, 0] = (Qd - self.Q) / delta
        dM_dshear_fd[:, 0] = (Md - self.M) / delta
        dP_dshear_fd[:, 0] = (Pd - self.P) / delta

        np.testing.assert_allclose(dT_dshear_fd, dT_dshear, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dQ_dshear_fd, dQ_dshear, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dM_dshear_fd, dM_dshear, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dP_dshear_fd, dP_dshear, rtol=5e-5, atol=1e-8)

    def test_dshear3(self):

        dCT_dshear = self.dCT["dshear"]
        dCQ_dshear = self.dCQ["dshear"]
        dCM_dshear = self.dCM["dshear"]
        dCP_dshear = self.dCP["dshear"]

        dCT_dshear_fd = np.zeros((self.npts, 1))
        dCQ_dshear_fd = np.zeros((self.npts, 1))
        dCM_dshear_fd = np.zeros((self.npts, 1))
        dCP_dshear_fd = np.zeros((self.npts, 1))

        shearExp = float(self.shearExp)
        delta = 1e-6
        shearExp += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
        CPd = outputs["CP"]
        CTd = outputs["CT"]
        CQd = outputs["CQ"]
        CMd = outputs["CM"]

        dCT_dshear_fd[:, 0] = (CTd - self.CT) / delta
        dCQ_dshear_fd[:, 0] = (CQd - self.CQ) / delta
        dCM_dshear_fd[:, 0] = (CMd - self.CM) / delta
        dCP_dshear_fd[:, 0] = (CPd - self.CP) / delta

        np.testing.assert_allclose(dCT_dshear_fd, dCT_dshear, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dCQ_dshear_fd, dCQ_dshear, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCM_dshear_fd, dCM_dshear, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCP_dshear_fd, dCP_dshear, rtol=5e-5, atol=1e-8)

    def test_dazimuth1(self):

        dNp_dazimuth = self.dNp["dazimuth"]
        dTp_dazimuth = self.dTp["dazimuth"]

        dNp_dazimuth_fd = np.zeros((self.n, 1))
        dTp_dazimuth_fd = np.zeros((self.n, 1))

        azimuth = float(self.azimuth)
        delta = 1e-6 * azimuth
        azimuth += delta

        outputs, _ = self.rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, azimuth)
        Npd = outputs["Np"]
        Tpd = outputs["Tp"]

        dNp_dazimuth_fd[:, 0] = (Npd - self.Np) / delta
        dTp_dazimuth_fd[:, 0] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dazimuth_fd, dNp_dazimuth, rtol=1e-5, atol=1e-6)
        np.testing.assert_allclose(dTp_dazimuth_fd, dTp_dazimuth, rtol=1e-5, atol=1e-6)

    def test_dUinf1(self):

        dNp_dUinf = self.dNp["dUinf"]
        dTp_dUinf = self.dTp["dUinf"]

        dNp_dUinf_fd = np.zeros((self.n, 1))
        dTp_dUinf_fd = np.zeros((self.n, 1))

        Uinf = float(self.Uinf)
        delta = 1e-6 * Uinf
        Uinf += delta

        outputs, _ = self.rotor.distributedAeroLoads(Uinf, self.Omega, self.pitch, self.azimuth)
        Npd = outputs["Np"]
        Tpd = outputs["Tp"]

        dNp_dUinf_fd[:, 0] = (Npd - self.Np) / delta
        dTp_dUinf_fd[:, 0] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dUinf_fd, dNp_dUinf, rtol=1e-5, atol=1e-6)
        np.testing.assert_allclose(dTp_dUinf_fd, dTp_dUinf, rtol=1e-5, atol=1e-6)

    def test_dUinf2(self):

        dT_dUinf = self.dT["dUinf"]
        dQ_dUinf = self.dQ["dUinf"]
        dM_dUinf = self.dM["dUinf"]
        dP_dUinf = self.dP["dUinf"]

        dT_dUinf_fd = np.zeros((self.npts, self.npts))
        dQ_dUinf_fd = np.zeros((self.npts, self.npts))
        dM_dUinf_fd = np.zeros((self.npts, self.npts))
        dP_dUinf_fd = np.zeros((self.npts, self.npts))

        Uinf = float(self.Uinf)
        delta = 1e-6 * Uinf
        Uinf += delta

        outputs, _ = self.rotor.evaluate([Uinf], [self.Omega], [self.pitch], coefficients=False)
        Pd = outputs["P"]
        Td = outputs["T"]
        Qd = outputs["Q"]
        Md = outputs["M"]

        dT_dUinf_fd[:, 0] = (Td - self.T) / delta
        dQ_dUinf_fd[:, 0] = (Qd - self.Q) / delta
        dM_dUinf_fd[:, 0] = (Md - self.M) / delta
        dP_dUinf_fd[:, 0] = (Pd - self.P) / delta

        np.testing.assert_allclose(dT_dUinf_fd, dT_dUinf, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dQ_dUinf_fd, dQ_dUinf, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dM_dUinf_fd, dM_dUinf, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dP_dUinf_fd, dP_dUinf, rtol=5e-5, atol=1e-8)

    def test_dUinf3(self):

        dCT_dUinf = self.dCT["dUinf"]
        dCQ_dUinf = self.dCQ["dUinf"]
        dCM_dUinf = self.dCM["dUinf"]
        dCP_dUinf = self.dCP["dUinf"]

        dCT_dUinf_fd = np.zeros((self.npts, self.npts))
        dCQ_dUinf_fd = np.zeros((self.npts, self.npts))
        dCM_dUinf_fd = np.zeros((self.npts, self.npts))
        dCP_dUinf_fd = np.zeros((self.npts, self.npts))

        Uinf = float(self.Uinf)
        delta = 1e-6 * Uinf
        Uinf += delta

        outputs, _ = self.rotor.evaluate([Uinf], [self.Omega], [self.pitch], coefficients=True)
        CPd = outputs["CP"]
        CTd = outputs["CT"]
        CQd = outputs["CQ"]
        CMd = outputs["CM"]

        dCT_dUinf_fd[:, 0] = (CTd - self.CT) / delta
        dCQ_dUinf_fd[:, 0] = (CQd - self.CQ) / delta
        dCM_dUinf_fd[:, 0] = (CMd - self.CM) / delta
        dCP_dUinf_fd[:, 0] = (CPd - self.CP) / delta

        np.testing.assert_allclose(dCT_dUinf_fd, dCT_dUinf, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dCQ_dUinf_fd, dCQ_dUinf, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCM_dUinf_fd, dCM_dUinf, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCP_dUinf_fd, dCP_dUinf, rtol=5e-5, atol=1e-8)

    def test_dOmega1(self):

        dNp_dOmega = self.dNp["dOmega"]
        dTp_dOmega = self.dTp["dOmega"]

        dNp_dOmega_fd = np.zeros((self.n, 1))
        dTp_dOmega_fd = np.zeros((self.n, 1))

        Omega = float(self.Omega)
        delta = 1e-6 * Omega
        Omega += delta

        loads, _ = self.rotor.distributedAeroLoads(self.Uinf, Omega, self.pitch, self.azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]

        dNp_dOmega_fd[:, 0] = (Npd - self.Np) / delta
        dTp_dOmega_fd[:, 0] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dOmega_fd, dNp_dOmega, rtol=1e-5, atol=1e-6)
        np.testing.assert_allclose(dTp_dOmega_fd, dTp_dOmega, rtol=1e-5, atol=1e-6)

    def test_dOmega2(self):

        dT_dOmega = self.dT["dOmega"]
        dQ_dOmega = self.dQ["dOmega"]
        dM_dOmega = self.dM["dOmega"]
        dP_dOmega = self.dP["dOmega"]

        dT_dOmega_fd = np.zeros((self.npts, self.npts))
        dQ_dOmega_fd = np.zeros((self.npts, self.npts))
        dM_dOmega_fd = np.zeros((self.npts, self.npts))
        dP_dOmega_fd = np.zeros((self.npts, self.npts))

        Omega = float(self.Omega)
        delta = 1e-6 * Omega
        Omega += delta

        outputs, _ = self.rotor.evaluate([self.Uinf], [Omega], [self.pitch], coefficients=False)
        Pd = outputs["P"]
        Td = outputs["T"]
        Qd = outputs["Q"]
        Md = outputs["M"]

        dT_dOmega_fd[:, 0] = (Td - self.T) / delta
        dQ_dOmega_fd[:, 0] = (Qd - self.Q) / delta
        dM_dOmega_fd[:, 0] = (Md - self.M) / delta
        dP_dOmega_fd[:, 0] = (Pd - self.P) / delta

        np.testing.assert_allclose(dT_dOmega_fd, dT_dOmega, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dQ_dOmega_fd, dQ_dOmega, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dM_dOmega_fd, dM_dOmega, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dP_dOmega_fd, dP_dOmega, rtol=5e-5, atol=1e-8)

    def test_dOmega3(self):

        dCT_dOmega = self.dCT["dOmega"]
        dCQ_dOmega = self.dCQ["dOmega"]
        dCM_dOmega = self.dCM["dOmega"]
        dCP_dOmega = self.dCP["dOmega"]

        dCT_dOmega_fd = np.zeros((self.npts, self.npts))
        dCQ_dOmega_fd = np.zeros((self.npts, self.npts))
        dCM_dOmega_fd = np.zeros((self.npts, self.npts))
        dCP_dOmega_fd = np.zeros((self.npts, self.npts))

        Omega = float(self.Omega)
        delta = 1e-6 * Omega
        Omega += delta

        outputs, _ = self.rotor.evaluate([self.Uinf], [Omega], [self.pitch], coefficients=True)
        CPd = outputs["CP"]
        CTd = outputs["CT"]
        CQd = outputs["CQ"]
        CMd = outputs["CM"]

        dCT_dOmega_fd[:, 0] = (CTd - self.CT) / delta
        dCQ_dOmega_fd[:, 0] = (CQd - self.CQ) / delta
        dCM_dOmega_fd[:, 0] = (CMd - self.CM) / delta
        dCP_dOmega_fd[:, 0] = (CPd - self.CP) / delta

        np.testing.assert_allclose(dCT_dOmega_fd, dCT_dOmega, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dCQ_dOmega_fd, dCQ_dOmega, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCM_dOmega_fd, dCM_dOmega, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCP_dOmega_fd, dCP_dOmega, rtol=5e-5, atol=1e-8)

    def test_dpitch1(self):

        dNp_dpitch = self.dNp["dpitch"]
        dTp_dpitch = self.dTp["dpitch"]

        dNp_dpitch_fd = np.zeros((self.n, 1))
        dTp_dpitch_fd = np.zeros((self.n, 1))

        pitch = float(self.pitch)
        delta = 1e-6
        pitch += delta

        loads, _ = self.rotor.distributedAeroLoads(self.Uinf, self.Omega, pitch, self.azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]

        dNp_dpitch_fd[:, 0] = (Npd - self.Np) / delta
        dTp_dpitch_fd[:, 0] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dpitch_fd, dNp_dpitch, rtol=5e-5, atol=1e-6)
        np.testing.assert_allclose(dTp_dpitch_fd, dTp_dpitch, rtol=5e-5, atol=1e-6)

    def test_dpitch2(self):

        dT_dpitch = self.dT["dpitch"]
        dQ_dpitch = self.dQ["dpitch"]
        dM_dpitch = self.dM["dpitch"]
        dP_dpitch = self.dP["dpitch"]

        dT_dpitch_fd = np.zeros((self.npts, 1))
        dQ_dpitch_fd = np.zeros((self.npts, 1))
        dM_dpitch_fd = np.zeros((self.npts, 1))
        dP_dpitch_fd = np.zeros((self.npts, 1))

        pitch = float(self.pitch)
        delta = 1e-6
        pitch += delta

        outputs, _ = self.rotor.evaluate([self.Uinf], [self.Omega], [pitch], coefficients=False)
        Pd = outputs["P"]
        Td = outputs["T"]
        Qd = outputs["Q"]
        Md = outputs["M"]

        dT_dpitch_fd[:, 0] = (Td - self.T) / delta
        dQ_dpitch_fd[:, 0] = (Qd - self.Q) / delta
        dM_dpitch_fd[:, 0] = (Md - self.M) / delta
        dP_dpitch_fd[:, 0] = (Pd - self.P) / delta

        np.testing.assert_allclose(dT_dpitch_fd, dT_dpitch, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dQ_dpitch_fd, dQ_dpitch, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dM_dpitch_fd, dM_dpitch, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dP_dpitch_fd, dP_dpitch, rtol=5e-5, atol=1e-8)

    def test_dpitch3(self):

        dCT_dpitch = self.dCT["dpitch"]
        dCQ_dpitch = self.dCQ["dpitch"]
        dCM_dpitch = self.dCM["dpitch"]
        dCP_dpitch = self.dCP["dpitch"]

        dCT_dpitch_fd = np.zeros((self.npts, 1))
        dCQ_dpitch_fd = np.zeros((self.npts, 1))
        dCM_dpitch_fd = np.zeros((self.npts, 1))
        dCP_dpitch_fd = np.zeros((self.npts, 1))

        pitch = float(self.pitch)
        delta = 1e-6
        pitch += delta

        outputs, _ = self.rotor.evaluate([self.Uinf], [self.Omega], [pitch], coefficients=True)
        CPd = outputs["CP"]
        CTd = outputs["CT"]
        CQd = outputs["CQ"]
        CMd = outputs["CM"]

        dCT_dpitch_fd[:, 0] = (CTd - self.CT) / delta
        dCQ_dpitch_fd[:, 0] = (CQd - self.CQ) / delta
        dCM_dpitch_fd[:, 0] = (CMd - self.CM) / delta
        dCP_dpitch_fd[:, 0] = (CPd - self.CP) / delta

        np.testing.assert_allclose(dCT_dpitch_fd, dCT_dpitch, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dCQ_dpitch_fd, dCQ_dpitch, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCM_dpitch_fd, dCM_dpitch, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCP_dpitch_fd, dCP_dpitch, rtol=5e-5, atol=1e-8)

    def test_dprecurve1(self):

        precurve = np.linspace(1, 10, self.n)
        precurveTip = 10.1
        precone = 0.0
        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=True,
            precurve=precurve,
            precurveTip=precurveTip,
        )

        loads, derivs = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Np = loads["Np"]
        Tp = loads["Tp"]
        dNp = derivs["dNp"]
        dTp = derivs["dTp"]

        dNp_dprecurve = dNp["dprecurve"]
        dTp_dprecurve = dTp["dprecurve"]

        dNp_dprecurve_fd = np.zeros((self.n, self.n))
        dTp_dprecurve_fd = np.zeros((self.n, self.n))

        for i in range(self.n):
            pc = np.array(precurve)
            delta = 1e-6 * pc[i]
            pc[i] += delta

            rotor = CCBlade(
                self.r,
                self.chord,
                self.theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
                precurve=pc,
                precurveTip=precurveTip,
            )

            loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
            Npd = loads["Np"]
            Tpd = loads["Tp"]

            dNp_dprecurve_fd[:, i] = (Npd - Np) / delta
            dTp_dprecurve_fd[:, i] = (Tpd - Tp) / delta

        np.testing.assert_allclose(dNp_dprecurve_fd, dNp_dprecurve, rtol=3e-4, atol=1e-8)
        np.testing.assert_allclose(dTp_dprecurve_fd, dTp_dprecurve, rtol=3e-4, atol=1e-8)

    def test_dprecurve2(self):

        precurve = np.linspace(1, 10, self.n)
        precurveTip = 10.1
        precone = 0.0
        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=True,
            precurve=precurve,
            precurveTip=precurveTip,
        )

        outputs, derivs = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
        P = outputs["P"]
        T = outputs["T"]
        Q = outputs["Q"]
        M = outputs["M"]
        dP = derivs["dP"]
        dT = derivs["dT"]
        dQ = derivs["dQ"]
        dM = derivs["dM"]

        dT_dprecurve = dT["dprecurve"]
        dQ_dprecurve = dQ["dprecurve"]
        dM_dprecurve = dM["dprecurve"]
        dP_dprecurve = dP["dprecurve"]

        dT_dprecurve_fd = np.zeros((self.npts, self.n))
        dQ_dprecurve_fd = np.zeros((self.npts, self.n))
        dM_dprecurve_fd = np.zeros((self.npts, self.n))
        dP_dprecurve_fd = np.zeros((self.npts, self.n))
        for i in range(self.n):
            pc = np.array(precurve)
            delta = 1e-6 * pc[i]
            pc[i] += delta

            rotor = CCBlade(
                self.r,
                self.chord,
                self.theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
                precurve=pc,
                precurveTip=precurveTip,
            )

            outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
            Pd = outputs["P"]
            Td = outputs["T"]
            Qd = outputs["Q"]
            Md = outputs["M"]

            dT_dprecurve_fd[:, i] = (Td - T) / delta
            dQ_dprecurve_fd[:, i] = (Qd - Q) / delta
            dM_dprecurve_fd[:, i] = (Md - M) / delta
            dP_dprecurve_fd[:, i] = (Pd - P) / delta

        np.testing.assert_allclose(dT_dprecurve_fd, dT_dprecurve, rtol=3e-4, atol=1e-8)
        np.testing.assert_allclose(dQ_dprecurve_fd, dQ_dprecurve, rtol=3e-4, atol=1e-8)
        np.testing.assert_allclose(dM_dprecurve_fd, dM_dprecurve, rtol=8e-4, atol=1e-8)
        np.testing.assert_allclose(dP_dprecurve_fd, dP_dprecurve, rtol=3e-4, atol=1e-8)

    def test_dprecurve3(self):

        precurve = np.linspace(1, 10, self.n)
        precurveTip = 10.1
        precone = 0.0
        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=True,
            precurve=precurve,
            precurveTip=precurveTip,
        )

        outputs, derivs = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
        CP = outputs["CP"]
        CT = outputs["CT"]
        CQ = outputs["CQ"]
        CM = outputs["CM"]
        dCP = derivs["dCP"]
        dCT = derivs["dCT"]
        dCQ = derivs["dCQ"]
        dCM = derivs["dCM"]

        dCT_dprecurve = dCT["dprecurve"]
        dCQ_dprecurve = dCQ["dprecurve"]
        dCM_dprecurve = dCM["dprecurve"]
        dCP_dprecurve = dCP["dprecurve"]

        dCT_dprecurve_fd = np.zeros((self.npts, self.n))
        dCQ_dprecurve_fd = np.zeros((self.npts, self.n))
        dCM_dprecurve_fd = np.zeros((self.npts, self.n))
        dCP_dprecurve_fd = np.zeros((self.npts, self.n))
        for i in range(self.n):
            pc = np.array(precurve)
            delta = 1e-6 * pc[i]
            pc[i] += delta

            rotor = CCBlade(
                self.r,
                self.chord,
                self.theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
                precurve=pc,
                precurveTip=precurveTip,
            )

            outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
            CPd = outputs["CP"]
            CTd = outputs["CT"]
            CQd = outputs["CQ"]
            CMd = outputs["CM"]

            dCT_dprecurve_fd[:, i] = (CTd - CT) / delta
            dCQ_dprecurve_fd[:, i] = (CQd - CQ) / delta
            dCM_dprecurve_fd[:, i] = (CMd - CM) / delta
            dCP_dprecurve_fd[:, i] = (CPd - CP) / delta

        np.testing.assert_allclose(dCT_dprecurve_fd, dCT_dprecurve, rtol=3e-4, atol=1e-8)
        np.testing.assert_allclose(dCQ_dprecurve_fd, dCQ_dprecurve, rtol=3e-4, atol=1e-8)
        np.testing.assert_allclose(dCM_dprecurve_fd, dCM_dprecurve, rtol=3e-4, atol=1e-8)
        np.testing.assert_allclose(dCP_dprecurve_fd, dCP_dprecurve, rtol=3e-4, atol=1e-8)

    def test_dpresweep1(self):

        presweep = np.linspace(1, 10, self.n)
        presweepTip = 10.1
        precone = 0.0
        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=True,
            presweep=presweep,
            presweepTip=presweepTip,
        )

        loads, derivs = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Np = loads["Np"]
        Tp = loads["Tp"]
        dNp = derivs["dNp"]
        dTp = derivs["dTp"]

        dNp_dpresweep = dNp["dpresweep"]
        dTp_dpresweep = dTp["dpresweep"]

        dNp_dpresweep_fd = np.zeros((self.n, self.n))
        dTp_dpresweep_fd = np.zeros((self.n, self.n))

        for i in range(self.n):
            ps = np.array(presweep)
            delta = 1e-6 * ps[i]
            ps[i] += delta

            rotor = CCBlade(
                self.r,
                self.chord,
                self.theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
                presweep=ps,
                presweepTip=presweepTip,
            )

            loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
            Npd = loads["Np"]
            Tpd = loads["Tp"]

            dNp_dpresweep_fd[:, i] = (Npd - Np) / delta
            dTp_dpresweep_fd[:, i] = (Tpd - Tp) / delta

        np.testing.assert_allclose(dNp_dpresweep_fd, dNp_dpresweep, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dTp_dpresweep_fd, dTp_dpresweep, rtol=1e-5, atol=1e-8)

    def test_dpresweep2(self):

        presweep = np.linspace(1, 10, self.n)
        presweepTip = 10.1
        precone = 0.0
        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=True,
            presweep=presweep,
            presweepTip=presweepTip,
        )

        outputs, derivs = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
        P = outputs["P"]
        T = outputs["T"]
        Q = outputs["Q"]
        M = outputs["M"]
        dP = derivs["dP"]
        dT = derivs["dT"]
        dQ = derivs["dQ"]
        dM = derivs["dM"]

        dT_dpresweep = dT["dpresweep"]
        dQ_dpresweep = dQ["dpresweep"]
        dM_dpresweep = dM["dpresweep"]
        dP_dpresweep = dP["dpresweep"]

        dT_dpresweep_fd = np.zeros((self.npts, self.n))
        dQ_dpresweep_fd = np.zeros((self.npts, self.n))
        dM_dpresweep_fd = np.zeros((self.npts, self.n))
        dP_dpresweep_fd = np.zeros((self.npts, self.n))
        for i in range(self.n):
            ps = np.array(presweep)
            delta = 1e-6 * ps[i]
            ps[i] += delta

            rotor = CCBlade(
                self.r,
                self.chord,
                self.theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
                presweep=ps,
                presweepTip=presweepTip,
            )

            outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
            Pd = outputs["P"]
            Td = outputs["T"]
            Qd = outputs["Q"]
            Md = outputs["M"]

            dT_dpresweep_fd[:, i] = (Td - T) / delta
            dQ_dpresweep_fd[:, i] = (Qd - Q) / delta
            dM_dpresweep_fd[:, i] = (Md - M) / delta
            dP_dpresweep_fd[:, i] = (Pd - P) / delta

        np.testing.assert_allclose(dT_dpresweep_fd, dT_dpresweep, rtol=3e-4, atol=1e-8)
        np.testing.assert_allclose(dQ_dpresweep_fd, dQ_dpresweep, rtol=3e-4, atol=1e-8)
        np.testing.assert_allclose(dM_dpresweep_fd, dM_dpresweep, rtol=3e-4, atol=1e-8)
        np.testing.assert_allclose(dP_dpresweep_fd, dP_dpresweep, rtol=3e-4, atol=1e-8)

    def test_dpresweep3(self):

        presweep = np.linspace(1, 10, self.n)
        presweepTip = 10.1
        precone = 0.0
        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=True,
            presweep=presweep,
            presweepTip=presweepTip,
        )

        outputs, derivs = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
        CP = outputs["CP"]
        CT = outputs["CT"]
        CQ = outputs["CQ"]
        CM = outputs["CM"]
        dCP = derivs["dCP"]
        dCT = derivs["dCT"]
        dCQ = derivs["dCQ"]
        dCM = derivs["dCM"]

        dCT_dpresweep = dCT["dpresweep"]
        dCQ_dpresweep = dCQ["dpresweep"]
        dCM_dpresweep = dCM["dpresweep"]
        dCP_dpresweep = dCP["dpresweep"]

        dCT_dpresweep_fd = np.zeros((self.npts, self.n))
        dCQ_dpresweep_fd = np.zeros((self.npts, self.n))
        dCM_dpresweep_fd = np.zeros((self.npts, self.n))
        dCP_dpresweep_fd = np.zeros((self.npts, self.n))
        for i in range(self.n):
            ps = np.array(presweep)
            delta = 1e-6 * ps[i]
            ps[i] += delta

            rotor = CCBlade(
                self.r,
                self.chord,
                self.theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
                presweep=ps,
                presweepTip=presweepTip,
            )

            outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
            CPd = outputs["CP"]
            CTd = outputs["CT"]
            CQd = outputs["CQ"]
            CMd = outputs["CM"]

            dCT_dpresweep_fd[:, i] = (CTd - CT) / delta
            dCQ_dpresweep_fd[:, i] = (CQd - CQ) / delta
            dCM_dpresweep_fd[:, i] = (CMd - CM) / delta
            dCP_dpresweep_fd[:, i] = (CPd - CP) / delta

        np.testing.assert_allclose(dCT_dpresweep_fd, dCT_dpresweep, rtol=3e-4, atol=1e-8)
        np.testing.assert_allclose(dCQ_dpresweep_fd, dCQ_dpresweep, rtol=3e-4, atol=1e-8)
        np.testing.assert_allclose(dCM_dpresweep_fd, dCM_dpresweep, rtol=3e-4, atol=1e-8)
        np.testing.assert_allclose(dCP_dpresweep_fd, dCP_dpresweep, rtol=3e-4, atol=1e-8)

    def test_dprecurveTip1(self):

        precurve = np.linspace(1, 10, self.n)
        precurveTip = 10.1
        precone = 0.0
        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=True,
            precurve=precurve,
            precurveTip=precurveTip,
        )

        loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Np = loads["Np"]
        Tp = loads["Tp"]

        dNp_dprecurveTip_fd = np.zeros((self.n, 1))
        dTp_dprecurveTip_fd = np.zeros((self.n, 1))

        pct = float(precurveTip)
        delta = 1e-6 * pct
        pct += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
            precurve=precurve,
            precurveTip=pct,
        )

        loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]
        dNp_dprecurveTip_fd[:, 0] = (Npd - Np) / delta
        dTp_dprecurveTip_fd[:, 0] = (Tpd - Tp) / delta

        np.testing.assert_allclose(dNp_dprecurveTip_fd, 0.0, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dTp_dprecurveTip_fd, 0.0, rtol=1e-4, atol=1e-8)

    def test_dprecurveTip2(self):

        precurve = np.linspace(1, 10, self.n)
        precurveTip = 10.1
        precone = 0.0
        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=True,
            precurve=precurve,
            precurveTip=precurveTip,
        )

        outputs, derivs = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
        P = outputs["P"]
        T = outputs["T"]
        Q = outputs["Q"]
        M = outputs["M"]
        dP = derivs["dP"]
        dT = derivs["dT"]
        dQ = derivs["dQ"]
        dM = derivs["dM"]

        dT_dprecurveTip = dT["dprecurveTip"]
        dQ_dprecurveTip = dQ["dprecurveTip"]
        dM_dprecurveTip = dM["dprecurveTip"]
        dP_dprecurveTip = dP["dprecurveTip"]

        dT_dprecurveTip_fd = np.zeros((self.npts, 1))
        dQ_dprecurveTip_fd = np.zeros((self.npts, 1))
        dM_dprecurveTip_fd = np.zeros((self.npts, 1))
        dP_dprecurveTip_fd = np.zeros((self.npts, 1))

        pct = float(precurveTip)
        delta = 1e-6 * pct
        pct += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
            precurve=precurve,
            precurveTip=pct,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
        Pd = outputs["P"]
        Td = outputs["T"]
        Qd = outputs["Q"]
        Md = outputs["M"]

        dT_dprecurveTip_fd[:, 0] = (Td - T) / delta
        dQ_dprecurveTip_fd[:, 0] = (Qd - Q) / delta
        dM_dprecurveTip_fd[:, 0] = (Md - M) / delta
        dP_dprecurveTip_fd[:, 0] = (Pd - P) / delta

        np.testing.assert_allclose(dT_dprecurveTip_fd, dT_dprecurveTip, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dQ_dprecurveTip_fd, dQ_dprecurveTip, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dM_dprecurveTip_fd, dM_dprecurveTip, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dP_dprecurveTip_fd, dP_dprecurveTip, rtol=1e-4, atol=1e-8)

    def test_dprecurveTip3(self):

        precurve = np.linspace(1, 10, self.n)
        precurveTip = 10.1
        precone = 0.0
        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=True,
            precurve=precurve,
            precurveTip=precurveTip,
        )

        outputs, derivs = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
        CP = outputs["CP"]
        CT = outputs["CT"]
        CQ = outputs["CQ"]
        CM = outputs["CM"]
        dCP = derivs["dCP"]
        dCT = derivs["dCT"]
        dCQ = derivs["dCQ"]
        dCM = derivs["dCM"]

        dCT_dprecurveTip = dCT["dprecurveTip"]
        dCQ_dprecurveTip = dCQ["dprecurveTip"]
        dCM_dprecurveTip = dCM["dprecurveTip"]
        dCP_dprecurveTip = dCP["dprecurveTip"]

        dCT_dprecurveTip_fd = np.zeros((self.npts, 1))
        dCQ_dprecurveTip_fd = np.zeros((self.npts, 1))
        dCM_dprecurveTip_fd = np.zeros((self.npts, 1))
        dCP_dprecurveTip_fd = np.zeros((self.npts, 1))

        pct = float(precurveTip)
        delta = 1e-6 * pct
        pct += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
            precurve=precurve,
            precurveTip=pct,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
        CPd = outputs["CP"]
        CTd = outputs["CT"]
        CQd = outputs["CQ"]
        CMd = outputs["CM"]

        dCT_dprecurveTip_fd[:, 0] = (CTd - CT) / delta
        dCQ_dprecurveTip_fd[:, 0] = (CQd - CQ) / delta
        dCM_dprecurveTip_fd[:, 0] = (CMd - CM) / delta
        dCP_dprecurveTip_fd[:, 0] = (CPd - CP) / delta

        np.testing.assert_allclose(dCT_dprecurveTip_fd, dCT_dprecurveTip, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dCQ_dprecurveTip_fd, dCQ_dprecurveTip, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dCM_dprecurveTip_fd, dCM_dprecurveTip, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dCP_dprecurveTip_fd, dCP_dprecurveTip, rtol=1e-4, atol=1e-8)

    def test_dpresweepTip1(self):

        presweep = np.linspace(1, 10, self.n)
        presweepTip = 10.1
        precone = 0.0
        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=True,
            presweep=presweep,
            presweepTip=presweepTip,
        )

        loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Np = loads["Np"]
        Tp = loads["Tp"]

        dNp_dpresweepTip_fd = np.zeros((self.n, 1))
        dTp_dpresweepTip_fd = np.zeros((self.n, 1))

        pst = float(presweepTip)
        delta = 1e-6 * pst
        pst += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
            presweep=presweep,
            presweepTip=pst,
        )

        loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]
        dNp_dpresweepTip_fd[:, 0] = (Npd - Np) / delta
        dTp_dpresweepTip_fd[:, 0] = (Tpd - Tp) / delta

        np.testing.assert_allclose(dNp_dpresweepTip_fd, 0.0, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dTp_dpresweepTip_fd, 0.0, rtol=1e-4, atol=1e-8)

    def test_dpresweepTip2(self):

        presweep = np.linspace(1, 10, self.n)
        presweepTip = 10.1
        precone = 0.0
        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=True,
            presweep=presweep,
            presweepTip=presweepTip,
        )

        outputs, derivs = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
        P = outputs["P"]
        T = outputs["T"]
        Q = outputs["Q"]
        M = outputs["M"]
        dP = derivs["dP"]
        dT = derivs["dT"]
        dQ = derivs["dQ"]
        dM = derivs["dM"]

        dT_dpresweepTip = dT["dpresweepTip"]
        dQ_dpresweepTip = dQ["dpresweepTip"]
        dM_dpresweepTip = dM["dpresweepTip"]
        dP_dpresweepTip = dP["dpresweepTip"]

        dT_dpresweepTip_fd = np.zeros((self.npts, 1))
        dQ_dpresweepTip_fd = np.zeros((self.npts, 1))
        dM_dpresweepTip_fd = np.zeros((self.npts, 1))
        dP_dpresweepTip_fd = np.zeros((self.npts, 1))

        pst = float(presweepTip)
        delta = 1e-6 * pst
        pst += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
            presweep=presweep,
            presweepTip=pst,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
        Pd = outputs["P"]
        Td = outputs["T"]
        Qd = outputs["Q"]
        Md = outputs["M"]

        dT_dpresweepTip_fd[:, 0] = (Td - T) / delta
        dQ_dpresweepTip_fd[:, 0] = (Qd - Q) / delta
        dM_dpresweepTip_fd[:, 0] = (Md - M) / delta
        dP_dpresweepTip_fd[:, 0] = (Pd - P) / delta

        np.testing.assert_allclose(dT_dpresweepTip_fd, dT_dpresweepTip, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dQ_dpresweepTip_fd, dQ_dpresweepTip, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dM_dpresweepTip_fd, dM_dpresweepTip, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dP_dpresweepTip_fd, dP_dpresweepTip, rtol=1e-4, atol=1e-8)

    def test_dpresweepTip3(self):

        presweep = np.linspace(1, 10, self.n)
        presweepTip = 10.1
        precone = 0.0
        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=True,
            presweep=presweep,
            presweepTip=presweepTip,
        )

        outputs, derivs = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
        CP = outputs["CP"]
        CT = outputs["CT"]
        CQ = outputs["CQ"]
        CM = outputs["CM"]
        dCP = derivs["dCP"]
        dCT = derivs["dCT"]
        dCQ = derivs["dCQ"]
        dCM = derivs["dCM"]

        dCT_dpresweepTip = dCT["dpresweepTip"]
        dCQ_dpresweepTip = dCQ["dpresweepTip"]
        dCM_dpresweepTip = dCM["dpresweepTip"]
        dCP_dpresweepTip = dCP["dpresweepTip"]

        dCT_dpresweepTip_fd = np.zeros((self.npts, 1))
        dCQ_dpresweepTip_fd = np.zeros((self.npts, 1))
        dCM_dpresweepTip_fd = np.zeros((self.npts, 1))
        dCP_dpresweepTip_fd = np.zeros((self.npts, 1))

        pst = float(presweepTip)
        delta = 1e-6 * pst
        pst += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
            presweep=presweep,
            presweepTip=pst,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
        CPd = outputs["CP"]
        CTd = outputs["CT"]
        CQd = outputs["CQ"]
        CMd = outputs["CM"]

        dCT_dpresweepTip_fd[:, 0] = (CTd - CT) / delta
        dCQ_dpresweepTip_fd[:, 0] = (CQd - CQ) / delta
        dCM_dpresweepTip_fd[:, 0] = (CMd - CM) / delta
        dCP_dpresweepTip_fd[:, 0] = (CPd - CP) / delta

        np.testing.assert_allclose(dCT_dpresweepTip_fd, dCT_dpresweepTip, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dCQ_dpresweepTip_fd, dCQ_dpresweepTip, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dCM_dpresweepTip_fd, dCM_dpresweepTip, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dCP_dpresweepTip_fd, dCP_dpresweepTip, rtol=1e-4, atol=1e-8)


class TestGradientsNotRotating(unittest.TestCase):
    def setUp(self):

        # geometry
        self.Rhub = 1.5
        self.Rtip = 63.0

        self.r = np.array(
            [
                2.8667,
                5.6000,
                8.3333,
                11.7500,
                15.8500,
                19.9500,
                24.0500,
                28.1500,
                32.2500,
                36.3500,
                40.4500,
                44.5500,
                48.6500,
                52.7500,
                56.1667,
                58.9000,
                61.6333,
            ]
        )
        self.chord = np.array(
            [
                3.542,
                3.854,
                4.167,
                4.557,
                4.652,
                4.458,
                4.249,
                4.007,
                3.748,
                3.502,
                3.256,
                3.010,
                2.764,
                2.518,
                2.313,
                2.086,
                1.419,
            ]
        )
        self.theta = np.array(
            [
                13.308,
                13.308,
                13.308,
                13.308,
                11.480,
                10.162,
                9.011,
                7.795,
                6.544,
                5.361,
                4.188,
                3.125,
                2.319,
                1.526,
                0.863,
                0.370,
                0.106,
            ]
        )
        self.B = 3  # number of blades

        # atmosphere
        self.rho = 1.225
        self.mu = 1.81206e-5

        afinit = CCAirfoil.initFromAerodynFile  # just for shorthand
        basepath = path.join(path.dirname(path.realpath(__file__)), "../../../examples/_airfoil_files/")

        # load all airfoils
        airfoil_types = [0] * 8
        airfoil_types[0] = afinit(basepath + "Cylinder1.dat")
        airfoil_types[1] = afinit(basepath + "Cylinder2.dat")
        airfoil_types[2] = afinit(basepath + "DU40_A17.dat")
        airfoil_types[3] = afinit(basepath + "DU35_A17.dat")
        airfoil_types[4] = afinit(basepath + "DU30_A17.dat")
        airfoil_types[5] = afinit(basepath + "DU25_A17.dat")
        airfoil_types[6] = afinit(basepath + "DU21_A17.dat")
        airfoil_types[7] = afinit(basepath + "NACA64_A17.dat")

        # place at appropriate radial stations
        af_idx = [0, 0, 1, 2, 3, 3, 4, 5, 5, 6, 6, 7, 7, 7, 7, 7, 7]

        self.af = [0] * len(self.r)
        for i in range(len(self.r)):
            self.af[i] = airfoil_types[af_idx[i]]

        self.tilt = -5.0
        self.precone = 2.5
        self.yaw = 0.0
        self.shearExp = 0.2
        self.hubHt = 80.0
        self.nSector = 8

        # create CCBlade object
        self.rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=True,
        )

        # set conditions
        self.Uinf = 10.0
        self.pitch = 0.0
        self.Omega = 0.0  # convert to RPM
        self.azimuth = 90

        loads, derivs = self.rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        self.Np = loads["Np"]
        self.Tp = loads["Tp"]
        self.dNp = derivs["dNp"]
        self.dTp = derivs["dTp"]

        self.rotor.derivatives = False
        self.n = len(self.r)
        self.npts = 1  # len(Uinf)

    def test_dr1(self):

        dNp_dr = self.dNp["dr"]
        dTp_dr = self.dTp["dr"]
        dNp_dr_fd = np.zeros((self.n, self.n))
        dTp_dr_fd = np.zeros((self.n, self.n))

        for i in range(self.n):
            r = np.array(self.r)
            delta = 1e-6 * r[i]
            r[i] += delta

            rotor = CCBlade(
                r,
                self.chord,
                self.theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                self.precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
            )

            loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
            Npd = loads["Np"]
            Tpd = loads["Tp"]

            dNp_dr_fd[:, i] = (Npd - self.Np) / delta
            dTp_dr_fd[:, i] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dr_fd, dNp_dr, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dTp_dr_fd, dTp_dr, rtol=1e-4, atol=1e-8)

    def test_dchord1(self):

        dNp_dchord = self.dNp["dchord"]
        dTp_dchord = self.dTp["dchord"]
        dNp_dchord_fd = np.zeros((self.n, self.n))
        dTp_dchord_fd = np.zeros((self.n, self.n))

        for i in range(self.n):
            chord = np.array(self.chord)
            delta = 1e-6 * chord[i]
            chord[i] += delta

            rotor = CCBlade(
                self.r,
                chord,
                self.theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                self.precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
            )

            loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
            Npd = loads["Np"]
            Tpd = loads["Tp"]

            dNp_dchord_fd[:, i] = (Npd - self.Np) / delta
            dTp_dchord_fd[:, i] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dchord_fd, dNp_dchord, rtol=1e-6, atol=1e-8)
        np.testing.assert_allclose(dTp_dchord_fd, dTp_dchord, rtol=5e-5, atol=1e-8)

    def test_dtheta1(self):

        dNp_dtheta = self.dNp["dtheta"]
        dTp_dtheta = self.dTp["dtheta"]
        dNp_dtheta_fd = np.zeros((self.n, self.n))
        dTp_dtheta_fd = np.zeros((self.n, self.n))

        for i in range(self.n):
            theta = np.array(self.theta)
            delta = 1e-6 * theta[i]
            theta[i] += delta

            rotor = CCBlade(
                self.r,
                self.chord,
                theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                self.precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
            )

            loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
            Npd = loads["Np"]
            Tpd = loads["Tp"]

            dNp_dtheta_fd[:, i] = (Npd - self.Np) / delta
            dTp_dtheta_fd[:, i] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dtheta_fd, dNp_dtheta, rtol=1e-6, atol=1e-6)
        np.testing.assert_allclose(dTp_dtheta_fd, dTp_dtheta, rtol=1e-4, atol=1e-6)

    def test_dRhub1(self):

        dNp_dRhub = self.dNp["dRhub"]
        dTp_dRhub = self.dTp["dRhub"]

        dNp_dRhub_fd = np.zeros((self.n, 1))
        dTp_dRhub_fd = np.zeros((self.n, 1))

        Rhub = float(self.Rhub)
        delta = 1e-6 * Rhub
        Rhub += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        loads, _ = self.rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]

        dNp_dRhub_fd[:, 0] = (Npd - self.Np) / delta
        dTp_dRhub_fd[:, 0] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dRhub_fd, dNp_dRhub, rtol=1e-5, atol=1e-7)
        np.testing.assert_allclose(dTp_dRhub_fd, dTp_dRhub, rtol=1e-4, atol=1e-7)

    def test_dRtip1(self):

        dNp_dRtip = self.dNp["dRtip"]
        dTp_dRtip = self.dTp["dRtip"]

        dNp_dRtip_fd = np.zeros((self.n, 1))
        dTp_dRtip_fd = np.zeros((self.n, 1))

        Rtip = float(self.Rtip)
        delta = 1e-6 * Rtip
        Rtip += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]

        dNp_dRtip_fd[:, 0] = (Npd - self.Np) / delta
        dTp_dRtip_fd[:, 0] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dRtip_fd, dNp_dRtip, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dTp_dRtip_fd, dTp_dRtip, rtol=1e-4, atol=1e-8)

    def test_dprecone1(self):

        dNp_dprecone = self.dNp["dprecone"]
        dTp_dprecone = self.dTp["dprecone"]

        dNp_dprecone_fd = np.zeros((self.n, 1))
        dTp_dprecone_fd = np.zeros((self.n, 1))

        precone = float(self.precone)
        delta = 1e-6 * precone
        precone += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]

        dNp_dprecone_fd[:, 0] = (Npd - self.Np) / delta
        dTp_dprecone_fd[:, 0] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dprecone_fd, dNp_dprecone, rtol=1e-6, atol=1e-8)
        np.testing.assert_allclose(dTp_dprecone_fd, dTp_dprecone, rtol=1e-6, atol=1e-8)

    def test_dtilt1(self):

        dNp_dtilt = self.dNp["dtilt"]
        dTp_dtilt = self.dTp["dtilt"]

        dNp_dtilt_fd = np.zeros((self.n, 1))
        dTp_dtilt_fd = np.zeros((self.n, 1))

        tilt = float(self.tilt)
        delta = 1e-6 * tilt
        tilt += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]

        dNp_dtilt_fd[:, 0] = (Npd - self.Np) / delta
        dTp_dtilt_fd[:, 0] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dtilt_fd, dNp_dtilt, rtol=1e-6, atol=1e-6)
        np.testing.assert_allclose(dTp_dtilt_fd, dTp_dtilt, rtol=1e-5, atol=1e-6)

    def test_dhubht1(self):

        dNp_dhubht = self.dNp["dhubHt"]
        dTp_dhubht = self.dTp["dhubHt"]

        dNp_dhubht_fd = np.zeros((self.n, 1))
        dTp_dhubht_fd = np.zeros((self.n, 1))

        hubht = float(self.hubHt)
        delta = 1e-6 * hubht
        hubht += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            hubht,
            self.nSector,
            derivatives=False,
        )

        loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]

        dNp_dhubht_fd[:, 0] = (Npd - self.Np) / delta
        dTp_dhubht_fd[:, 0] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dhubht_fd, dNp_dhubht, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dTp_dhubht_fd, dTp_dhubht, rtol=1e-5, atol=1e-8)

    def test_dyaw1(self):

        dNp_dyaw = self.dNp["dyaw"]
        dTp_dyaw = self.dTp["dyaw"]

        dNp_dyaw_fd = np.zeros((self.n, 1))
        dTp_dyaw_fd = np.zeros((self.n, 1))

        yaw = float(self.yaw)
        delta = 1e-6
        yaw += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]

        dNp_dyaw_fd[:, 0] = (Npd - self.Np) / delta
        dTp_dyaw_fd[:, 0] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dyaw_fd, dNp_dyaw, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dTp_dyaw_fd, dTp_dyaw, rtol=1e-5, atol=1e-8)

    def test_dshear1(self):

        dNp_dshear = self.dNp["dshear"]
        dTp_dshear = self.dTp["dshear"]

        dNp_dshear_fd = np.zeros((self.n, 1))
        dTp_dshear_fd = np.zeros((self.n, 1))

        shearExp = float(self.shearExp)
        delta = 1e-6
        shearExp += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]

        dNp_dshear_fd[:, 0] = (Npd - self.Np) / delta
        dTp_dshear_fd[:, 0] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dshear_fd, dNp_dshear, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dTp_dshear_fd, dTp_dshear, rtol=1e-5, atol=1e-8)

    def test_dazimuth1(self):

        dNp_dazimuth = self.dNp["dazimuth"]
        dTp_dazimuth = self.dTp["dazimuth"]

        dNp_dazimuth_fd = np.zeros((self.n, 1))
        dTp_dazimuth_fd = np.zeros((self.n, 1))

        azimuth = float(self.azimuth)
        delta = 1e-6 * azimuth
        azimuth += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        loads, _ = self.rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]

        dNp_dazimuth_fd[:, 0] = (Npd - self.Np) / delta
        dTp_dazimuth_fd[:, 0] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dazimuth_fd, dNp_dazimuth, rtol=1e-5, atol=1e-6)
        np.testing.assert_allclose(dTp_dazimuth_fd, dTp_dazimuth, rtol=1e-5, atol=1e-6)

    def test_dUinf1(self):

        dNp_dUinf = self.dNp["dUinf"]
        dTp_dUinf = self.dTp["dUinf"]

        dNp_dUinf_fd = np.zeros((self.n, 1))
        dTp_dUinf_fd = np.zeros((self.n, 1))

        Uinf = float(self.Uinf)
        delta = 1e-6 * Uinf
        Uinf += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        loads, _ = self.rotor.distributedAeroLoads(Uinf, self.Omega, self.pitch, self.azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]

        dNp_dUinf_fd[:, 0] = (Npd - self.Np) / delta
        dTp_dUinf_fd[:, 0] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dUinf_fd, dNp_dUinf, rtol=1e-5, atol=1e-6)
        np.testing.assert_allclose(dTp_dUinf_fd, dTp_dUinf, rtol=1e-5, atol=1e-6)

    #
    # Omega is fixed at 0 so no need to run derivatives test
    #

    def test_dpitch1(self):

        dNp_dpitch = self.dNp["dpitch"]
        dTp_dpitch = self.dTp["dpitch"]

        dNp_dpitch_fd = np.zeros((self.n, 1))
        dTp_dpitch_fd = np.zeros((self.n, 1))

        pitch = float(self.pitch)
        delta = 1e-6
        pitch += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        loads, _ = self.rotor.distributedAeroLoads(self.Uinf, self.Omega, pitch, self.azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]

        dNp_dpitch_fd[:, 0] = (Npd - self.Np) / delta
        dTp_dpitch_fd[:, 0] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dpitch_fd, dNp_dpitch, rtol=5e-5, atol=1e-6)
        np.testing.assert_allclose(dTp_dpitch_fd, dTp_dpitch, rtol=5e-5, atol=1e-6)

    def test_dprecurve1(self):

        precurve = np.linspace(1, 10, self.n)
        precurveTip = 10.1
        precone = 0.0
        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=True,
            precurve=precurve,
            precurveTip=precurveTip,
        )

        loads, derivs = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Np = loads["Np"]
        Tp = loads["Tp"]
        dNp = derivs["dNp"]
        dTp = derivs["dTp"]

        dNp_dprecurve = dNp["dprecurve"]
        dTp_dprecurve = dTp["dprecurve"]

        dNp_dprecurve_fd = np.zeros((self.n, self.n))
        dTp_dprecurve_fd = np.zeros((self.n, self.n))
        for i in range(self.n):
            pc = np.array(precurve)
            delta = 1e-6 * pc[i]
            pc[i] += delta

            rotor = CCBlade(
                self.r,
                self.chord,
                self.theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
                precurve=pc,
                precurveTip=precurveTip,
            )

            loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
            Npd = loads["Np"]
            Tpd = loads["Tp"]

            dNp_dprecurve_fd[:, i] = (Npd - Np) / delta
            dTp_dprecurve_fd[:, i] = (Tpd - Tp) / delta

        np.testing.assert_allclose(dNp_dprecurve_fd, dNp_dprecurve, rtol=3e-4, atol=1e-8)
        np.testing.assert_allclose(dTp_dprecurve_fd, dTp_dprecurve, rtol=3e-4, atol=1e-8)

    def test_dpresweep1(self):

        presweep = np.linspace(1, 10, self.n)
        presweepTip = 10.1
        precone = 0.0
        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=True,
            presweep=presweep,
            presweepTip=presweepTip,
        )

        loads, derivs = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Np = loads["Np"]
        Tp = loads["Tp"]
        dNp = derivs["dNp"]
        dTp = derivs["dTp"]

        dNp_dpresweep = dNp["dpresweep"]
        dTp_dpresweep = dTp["dpresweep"]

        dNp_dpresweep_fd = np.zeros((self.n, self.n))
        dTp_dpresweep_fd = np.zeros((self.n, self.n))
        for i in range(self.n):
            ps = np.array(presweep)
            delta = 1e-6 * ps[i]
            ps[i] += delta

            rotor = CCBlade(
                self.r,
                self.chord,
                self.theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
                presweep=ps,
                presweepTip=presweepTip,
            )

            loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
            Npd = loads["Np"]
            Tpd = loads["Tp"]

            dNp_dpresweep_fd[:, i] = (Npd - Np) / delta
            dTp_dpresweep_fd[:, i] = (Tpd - Tp) / delta

        np.testing.assert_allclose(dNp_dpresweep_fd, dNp_dpresweep, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dTp_dpresweep_fd, dTp_dpresweep, rtol=1e-5, atol=1e-8)

    def test_dprecurveTip1(self):

        precurve = np.linspace(1, 10, self.n)
        precurveTip = 10.1
        precone = 0.0
        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=True,
            precurve=precurve,
            precurveTip=precurveTip,
        )

        loads, derivs = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Np = loads["Np"]
        Tp = loads["Tp"]
        dNp = derivs["dNp"]
        dTp = derivs["dTp"]

        dNp_dprecurveTip_fd = np.zeros((self.n, 1))
        dTp_dprecurveTip_fd = np.zeros((self.n, 1))

        pct = float(precurveTip)
        delta = 1e-6 * pct
        pct += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
            precurve=precurve,
            precurveTip=pct,
        )

        loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]
        dNp_dprecurveTip_fd[:, 0] = (Npd - Np) / delta
        dTp_dprecurveTip_fd[:, 0] = (Tpd - Tp) / delta

        np.testing.assert_allclose(dNp_dprecurveTip_fd, 0.0, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dTp_dprecurveTip_fd, 0.0, rtol=1e-4, atol=1e-8)

    def test_dpresweepTip1(self):

        presweep = np.linspace(1, 10, self.n)
        presweepTip = 10.1
        precone = 0.0
        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=True,
            presweep=presweep,
            presweepTip=presweepTip,
        )

        loads, derivs = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Np = loads["Np"]
        Tp = loads["Tp"]
        dNp = derivs["dNp"]
        dTp = derivs["dTp"]

        dNp_dpresweepTip_fd = np.zeros((self.n, 1))
        dTp_dpresweepTip_fd = np.zeros((self.n, 1))

        pst = float(presweepTip)
        delta = 1e-6 * pst
        pst += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
            presweep=presweep,
            presweepTip=pst,
        )

        loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]
        dNp_dpresweepTip_fd[:, 0] = (Npd - Np) / delta
        dTp_dpresweepTip_fd[:, 0] = (Tpd - Tp) / delta

        np.testing.assert_allclose(dNp_dpresweepTip_fd, 0.0, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dTp_dpresweepTip_fd, 0.0, rtol=1e-4, atol=1e-8)


class TestGradientsFreestreamArray(unittest.TestCase):
    def setUp(self):

        # geometry
        self.Rhub = 1.5
        self.Rtip = 63.0

        self.r = np.array(
            [
                2.8667,
                5.6000,
                8.3333,
                11.7500,
                15.8500,
                19.9500,
                24.0500,
                28.1500,
                32.2500,
                36.3500,
                40.4500,
                44.5500,
                48.6500,
                52.7500,
                56.1667,
                58.9000,
                61.6333,
            ]
        )
        self.chord = np.array(
            [
                3.542,
                3.854,
                4.167,
                4.557,
                4.652,
                4.458,
                4.249,
                4.007,
                3.748,
                3.502,
                3.256,
                3.010,
                2.764,
                2.518,
                2.313,
                2.086,
                1.419,
            ]
        )
        self.theta = np.array(
            [
                13.308,
                13.308,
                13.308,
                13.308,
                11.480,
                10.162,
                9.011,
                7.795,
                6.544,
                5.361,
                4.188,
                3.125,
                2.319,
                1.526,
                0.863,
                0.370,
                0.106,
            ]
        )
        self.B = 3  # number of blades

        # atmosphere
        self.rho = 1.225
        self.mu = 1.81206e-5

        afinit = CCAirfoil.initFromAerodynFile  # just for shorthand
        basepath = path.join(path.dirname(path.realpath(__file__)), "../../../examples/_airfoil_files/")

        # load all airfoils
        airfoil_types = [0] * 8
        airfoil_types[0] = afinit(basepath + "Cylinder1.dat")
        airfoil_types[1] = afinit(basepath + "Cylinder2.dat")
        airfoil_types[2] = afinit(basepath + "DU40_A17.dat")
        airfoil_types[3] = afinit(basepath + "DU35_A17.dat")
        airfoil_types[4] = afinit(basepath + "DU30_A17.dat")
        airfoil_types[5] = afinit(basepath + "DU25_A17.dat")
        airfoil_types[6] = afinit(basepath + "DU21_A17.dat")
        airfoil_types[7] = afinit(basepath + "NACA64_A17.dat")

        # place at appropriate radial stations
        af_idx = [0, 0, 1, 2, 3, 3, 4, 5, 5, 6, 6, 7, 7, 7, 7, 7, 7]

        self.af = [0] * len(self.r)
        for i in range(len(self.r)):
            self.af[i] = airfoil_types[af_idx[i]]

        self.tilt = -5.0
        self.precone = 2.5
        self.yaw = 0.0
        self.shearExp = 0.2
        self.hubHt = 80.0
        self.nSector = 8

        # create CCBlade object
        self.rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=True,
        )

        # set conditions
        self.Uinf = np.array([10.0, 11.0, 12.0])
        tsr = 7.55
        self.pitch = np.zeros(3)
        self.Omega = self.Uinf * tsr / self.Rtip * 30.0 / pi  # convert to RPM

        outputs, derivs = self.rotor.evaluate(self.Uinf, self.Omega, self.pitch, coefficients=False)
        self.P, self.T, self.Q = [outputs[k] for k in ("P", "T", "Q")]
        self.P, self.T, self.M = [outputs[k] for k in ("P", "T", "M")]
        self.dP, self.dT, self.dQ = [derivs[k] for k in ("dP", "dT", "dQ")]
        self.dP, self.dT, self.dM = [derivs[k] for k in ("dP", "dT", "dM")]

        outputs, derivs = self.rotor.evaluate(self.Uinf, self.Omega, self.pitch, coefficients=True)
        self.CP, self.CT, self.CQ = [outputs[k] for k in ("CP", "CT", "CQ")]
        self.CP, self.CT, self.CM = [outputs[k] for k in ("CP", "CT", "CM")]
        self.dCP, self.dCT, self.dCQ = [derivs[k] for k in ("dCP", "dCT", "dCQ")]
        self.dCP, self.dCT, self.dCM = [derivs[k] for k in ("dCP", "dCT", "dCM")]

        self.rotor.derivatives = False
        self.n = len(self.r)
        self.npts = len(self.Uinf)

    def test_dUinf2(self):

        dT_dUinf = self.dT["dUinf"]
        dQ_dUinf = self.dQ["dUinf"]
        dM_dUinf = self.dM["dUinf"]
        dP_dUinf = self.dP["dUinf"]

        dT_dUinf_fd = np.zeros((self.npts, self.npts))
        dQ_dUinf_fd = np.zeros((self.npts, self.npts))
        dM_dUinf_fd = np.zeros((self.npts, self.npts))
        dP_dUinf_fd = np.zeros((self.npts, self.npts))

        for i in range(self.npts):
            Uinf = np.copy(self.Uinf)
            delta = 1e-6 * Uinf[i]
            Uinf[i] += delta

            outputs, _ = self.rotor.evaluate(Uinf, self.Omega, self.pitch, coefficients=False)
            Pd = outputs["P"]
            Td = outputs["T"]
            Qd = outputs["Q"]
            Md = outputs["M"]

            dT_dUinf_fd[:, i] = (Td - self.T) / delta
            dQ_dUinf_fd[:, i] = (Qd - self.Q) / delta
            dM_dUinf_fd[:, i] = (Md - self.M) / delta
            dP_dUinf_fd[:, i] = (Pd - self.P) / delta

        np.testing.assert_allclose(dT_dUinf_fd, dT_dUinf, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dQ_dUinf_fd, dQ_dUinf, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dM_dUinf_fd, dM_dUinf, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dP_dUinf_fd, dP_dUinf, rtol=5e-5, atol=1e-8)

    def test_dUinf3(self):

        dCT_dUinf = self.dCT["dUinf"]
        dCQ_dUinf = self.dCQ["dUinf"]
        dCM_dUinf = self.dCM["dUinf"]
        dCP_dUinf = self.dCP["dUinf"]

        dCT_dUinf_fd = np.zeros((self.npts, self.npts))
        dCQ_dUinf_fd = np.zeros((self.npts, self.npts))
        dCM_dUinf_fd = np.zeros((self.npts, self.npts))
        dCP_dUinf_fd = np.zeros((self.npts, self.npts))

        for i in range(self.npts):
            Uinf = np.copy(self.Uinf)
            delta = 1e-6 * Uinf[i]
            Uinf[i] += delta

            outputs, _ = self.rotor.evaluate(Uinf, self.Omega, self.pitch, coefficients=True)
            CPd = outputs["CP"]
            CTd = outputs["CT"]
            CQd = outputs["CQ"]
            CMd = outputs["CM"]

            dCT_dUinf_fd[:, i] = (CTd - self.CT) / delta
            dCQ_dUinf_fd[:, i] = (CQd - self.CQ) / delta
            dCM_dUinf_fd[:, i] = (CMd - self.CM) / delta
            dCP_dUinf_fd[:, i] = (CPd - self.CP) / delta

        np.testing.assert_allclose(dCT_dUinf_fd, dCT_dUinf, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dCQ_dUinf_fd, dCQ_dUinf, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCM_dUinf_fd, dCM_dUinf, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCP_dUinf_fd, dCP_dUinf, rtol=5e-5, atol=1e-8)

    def test_dOmega2(self):

        dT_dOmega = self.dT["dOmega"]
        dQ_dOmega = self.dQ["dOmega"]
        dM_dOmega = self.dM["dOmega"]
        dP_dOmega = self.dP["dOmega"]

        dT_dOmega_fd = np.zeros((self.npts, self.npts))
        dQ_dOmega_fd = np.zeros((self.npts, self.npts))
        dM_dOmega_fd = np.zeros((self.npts, self.npts))
        dP_dOmega_fd = np.zeros((self.npts, self.npts))

        for i in range(self.npts):
            Omega = np.copy(self.Omega)
            delta = 1e-6 * Omega[i]
            Omega[i] += delta

            outputs, _ = self.rotor.evaluate(self.Uinf, Omega, self.pitch, coefficients=False)
            Pd = outputs["P"]
            Td = outputs["T"]
            Qd = outputs["Q"]
            Md = outputs["M"]

            dT_dOmega_fd[:, i] = (Td - self.T) / delta
            dQ_dOmega_fd[:, i] = (Qd - self.Q) / delta
            dM_dOmega_fd[:, i] = (Md - self.M) / delta
            dP_dOmega_fd[:, i] = (Pd - self.P) / delta

        np.testing.assert_allclose(dT_dOmega_fd, dT_dOmega, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dQ_dOmega_fd, dQ_dOmega, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dM_dOmega_fd, dM_dOmega, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dP_dOmega_fd, dP_dOmega, rtol=5e-5, atol=1e-8)

    def test_dOmega3(self):

        dCT_dOmega = self.dCT["dOmega"]
        dCQ_dOmega = self.dCQ["dOmega"]
        dCM_dOmega = self.dCM["dOmega"]
        dCP_dOmega = self.dCP["dOmega"]

        dCT_dOmega_fd = np.zeros((self.npts, self.npts))
        dCQ_dOmega_fd = np.zeros((self.npts, self.npts))
        dCM_dOmega_fd = np.zeros((self.npts, self.npts))
        dCP_dOmega_fd = np.zeros((self.npts, self.npts))

        for i in range(self.npts):
            Omega = np.copy(self.Omega)
            delta = 1e-6 * Omega[i]
            Omega[i] += delta

            outputs, _ = self.rotor.evaluate(self.Uinf, Omega, self.pitch, coefficients=True)
            CPd = outputs["CP"]
            CTd = outputs["CT"]
            CQd = outputs["CQ"]
            CMd = outputs["CM"]

            dCT_dOmega_fd[:, i] = (CTd - self.CT) / delta
            dCQ_dOmega_fd[:, i] = (CQd - self.CQ) / delta
            dCM_dOmega_fd[:, i] = (CMd - self.CM) / delta
            dCP_dOmega_fd[:, i] = (CPd - self.CP) / delta

        np.testing.assert_allclose(dCT_dOmega_fd, dCT_dOmega, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dCQ_dOmega_fd, dCQ_dOmega, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCM_dOmega_fd, dCM_dOmega, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCP_dOmega_fd, dCP_dOmega, rtol=5e-5, atol=1e-8)

    def test_dpitch2(self):

        dT_dpitch = self.dT["dpitch"]
        dQ_dpitch = self.dQ["dpitch"]
        dM_dpitch = self.dM["dpitch"]
        dP_dpitch = self.dP["dpitch"]

        dT_dpitch_fd = np.zeros((self.npts, self.npts))
        dQ_dpitch_fd = np.zeros((self.npts, self.npts))
        dM_dpitch_fd = np.zeros((self.npts, self.npts))
        dP_dpitch_fd = np.zeros((self.npts, self.npts))

        for i in range(self.npts):
            pitch = np.copy(self.pitch)
            delta = 1e-6
            pitch[i] += delta

            outputs, _ = self.rotor.evaluate(self.Uinf, self.Omega, pitch, coefficients=False)
            Pd = outputs["P"]
            Td = outputs["T"]
            Qd = outputs["Q"]
            Md = outputs["M"]

            dT_dpitch_fd[:, i] = (Td - self.T) / delta
            dQ_dpitch_fd[:, i] = (Qd - self.Q) / delta
            dM_dpitch_fd[:, i] = (Md - self.M) / delta
            dP_dpitch_fd[:, i] = (Pd - self.P) / delta

        np.testing.assert_allclose(dT_dpitch_fd, dT_dpitch, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dQ_dpitch_fd, dQ_dpitch, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dM_dpitch_fd, dM_dpitch, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dP_dpitch_fd, dP_dpitch, rtol=5e-5, atol=1e-8)

    def test_dpitch3(self):

        dCT_dpitch = self.dCT["dpitch"]
        dCQ_dpitch = self.dCQ["dpitch"]
        dCM_dpitch = self.dCM["dpitch"]
        dCP_dpitch = self.dCP["dpitch"]

        dCT_dpitch_fd = np.zeros((self.npts, self.npts))
        dCQ_dpitch_fd = np.zeros((self.npts, self.npts))
        dCM_dpitch_fd = np.zeros((self.npts, self.npts))
        dCP_dpitch_fd = np.zeros((self.npts, self.npts))

        for i in range(self.npts):
            pitch = np.copy(self.pitch)
            delta = 1e-6
            pitch[i] += delta

            outputs, _ = self.rotor.evaluate(self.Uinf, self.Omega, pitch, coefficients=True)
            CPd = outputs["CP"]
            CTd = outputs["CT"]
            CQd = outputs["CQ"]
            CMd = outputs["CM"]

            dCT_dpitch_fd[:, i] = (CTd - self.CT) / delta
            dCQ_dpitch_fd[:, i] = (CQd - self.CQ) / delta
            dCM_dpitch_fd[:, i] = (CMd - self.CM) / delta
            dCP_dpitch_fd[:, i] = (CPd - self.CP) / delta

        np.testing.assert_allclose(dCT_dpitch_fd, dCT_dpitch, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dCQ_dpitch_fd, dCQ_dpitch, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCM_dpitch_fd, dCM_dpitch, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCP_dpitch_fd, dCP_dpitch, rtol=5e-5, atol=1e-8)


class TestGradients_RHub_Tip(unittest.TestCase):
    def setUp(self):

        # geometry
        self.Rhub = 1.5
        self.Rtip = 63.0

        self.r = np.array(
            [
                self.Rhub,
                5.6000,
                8.3333,
                11.7500,
                15.8500,
                19.9500,
                24.0500,
                28.1500,
                32.2500,
                36.3500,
                40.4500,
                44.5500,
                48.6500,
                52.7500,
                56.1667,
                58.9000,
                self.Rtip,
            ]
        )
        self.chord = np.array(
            [
                3.542,
                3.854,
                4.167,
                4.557,
                4.652,
                4.458,
                4.249,
                4.007,
                3.748,
                3.502,
                3.256,
                3.010,
                2.764,
                2.518,
                2.313,
                2.086,
                1.419,
            ]
        )
        self.theta = np.array(
            [
                13.308,
                13.308,
                13.308,
                13.308,
                11.480,
                10.162,
                9.011,
                7.795,
                6.544,
                5.361,
                4.188,
                3.125,
                2.319,
                1.526,
                0.863,
                0.370,
                0.106,
            ]
        )
        self.B = 3  # number of blades

        # atmosphere
        self.rho = 1.225
        self.mu = 1.81206e-5

        afinit = CCAirfoil.initFromAerodynFile  # just for shorthand
        basepath = path.join(path.dirname(path.realpath(__file__)), "../../../examples/_airfoil_files/")

        # load all airfoils
        airfoil_types = [0] * 8
        airfoil_types[0] = afinit(basepath + "Cylinder1.dat")
        airfoil_types[1] = afinit(basepath + "Cylinder2.dat")
        airfoil_types[2] = afinit(basepath + "DU40_A17.dat")
        airfoil_types[3] = afinit(basepath + "DU35_A17.dat")
        airfoil_types[4] = afinit(basepath + "DU30_A17.dat")
        airfoil_types[5] = afinit(basepath + "DU25_A17.dat")
        airfoil_types[6] = afinit(basepath + "DU21_A17.dat")
        airfoil_types[7] = afinit(basepath + "NACA64_A17.dat")

        # place at appropriate radial stations
        af_idx = [0, 0, 1, 2, 3, 3, 4, 5, 5, 6, 6, 7, 7, 7, 7, 7, 7]

        self.af = [0] * len(self.r)
        for i in range(len(self.r)):
            self.af[i] = airfoil_types[af_idx[i]]

        self.tilt = -5.0
        self.precone = 2.5
        self.yaw = 0.0
        self.shearExp = 0.2
        self.hubHt = 80.0
        self.nSector = 8

        # create CCBlade object
        self.rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=True,
        )

        # Update for FDs
        self.r = self.rotor.r.copy()

        # set conditions
        self.Uinf = 10.0
        tsr = 7.55
        self.pitch = 0.0
        self.Omega = self.Uinf * tsr / self.Rtip * 30.0 / pi  # convert to RPM
        self.azimuth = 90

        loads, derivs = self.rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        self.Np = loads["Np"]
        self.Tp = loads["Tp"]
        self.dNp = derivs["dNp"]
        self.dTp = derivs["dTp"]

        outputs, derivs = self.rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
        self.P, self.T, self.Q, self.M = [outputs[k] for k in ("P", "T", "Q", "M")]
        self.P, self.T, self.M, self.M = [outputs[k] for k in ("P", "T", "M", "M")]
        self.dP, self.dT, self.dQ = [derivs[k] for k in ("dP", "dT", "dQ")]
        self.dP, self.dT, self.dM = [derivs[k] for k in ("dP", "dT", "dM")]

        outputs, derivs = self.rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
        self.CP, self.CT, self.CQ, self.CM = [outputs[k] for k in ("CP", "CT", "CQ", "CM")]
        self.CP, self.CT, self.CM, self.CM = [outputs[k] for k in ("CP", "CT", "CM", "CM")]
        self.dCP, self.dCT, self.dCQ = [derivs[k] for k in ("dCP", "dCT", "dCQ")]
        self.dCP, self.dCT, self.dCM = [derivs[k] for k in ("dCP", "dCT", "dCM")]

        self.rotor.derivatives = False
        self.n = len(self.r)
        self.npts = 1  # len(Uinf)

    def test_dr1(self):

        dNp_dr = self.dNp["dr"]
        dTp_dr = self.dTp["dr"]
        dNp_dr_fd = np.zeros((self.n, self.n))
        dTp_dr_fd = np.zeros((self.n, self.n))

        for i in range(self.n):
            r = np.array(self.r)
            delta = 1e-6 * r[i]
            r[i] += delta

            rotor = CCBlade(
                r,
                self.chord,
                self.theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                self.precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
            )

            loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
            Npd = loads["Np"]
            Tpd = loads["Tp"]

            dNp_dr_fd[:, i] = (Npd - self.Np) / delta
            dTp_dr_fd[:, i] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dr_fd, dNp_dr, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dTp_dr_fd, dTp_dr, rtol=1e-4, atol=1e-8)

    def test_dr2(self):

        dT_dr = self.dT["dr"]
        dQ_dr = self.dQ["dr"]
        dM_dr = self.dM["dr"]
        dP_dr = self.dP["dr"]
        dT_dr_fd = np.zeros((self.npts, self.n))
        dQ_dr_fd = np.zeros((self.npts, self.n))
        dM_dr_fd = np.zeros((self.npts, self.n))
        dP_dr_fd = np.zeros((self.npts, self.n))

        for i in range(self.n):
            r = np.array(self.r)
            delta = 1e-6 * r[i]
            r[i] += delta

            rotor = CCBlade(
                r,
                self.chord,
                self.theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                self.precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
            )

            outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
            Pd = outputs["P"]
            Td = outputs["T"]
            Qd = outputs["Q"]
            Md = outputs["M"]

            dT_dr_fd[:, i] = (Td - self.T) / delta
            dQ_dr_fd[:, i] = (Qd - self.Q) / delta
            dM_dr_fd[:, i] = (Md - self.M) / delta
            dP_dr_fd[:, i] = (Pd - self.P) / delta

        np.testing.assert_allclose(dT_dr_fd, dT_dr, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dQ_dr_fd, dQ_dr, rtol=1e-3)  # , atol=1e-8)
        np.testing.assert_allclose(dM_dr_fd, dM_dr, rtol=1e-3)  # , atol=1e-8)
        np.testing.assert_allclose(dP_dr_fd, dP_dr, rtol=1e-3)  # , atol=1e-8)

    def test_dr3(self):

        dCT_dr = self.dCT["dr"]
        dCQ_dr = self.dCQ["dr"]
        dCM_dr = self.dCM["dr"]
        dCP_dr = self.dCP["dr"]
        dCT_dr_fd = np.zeros((self.npts, self.n))
        dCQ_dr_fd = np.zeros((self.npts, self.n))
        dCM_dr_fd = np.zeros((self.npts, self.n))
        dCP_dr_fd = np.zeros((self.npts, self.n))

        for i in range(self.n):
            r = np.array(self.r)
            delta = 1e-6 * r[i]
            r[i] += delta

            rotor = CCBlade(
                r,
                self.chord,
                self.theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                self.precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
            )

            outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
            CPd = outputs["CP"]
            CTd = outputs["CT"]
            CQd = outputs["CQ"]
            CMd = outputs["CM"]

            dCT_dr_fd[:, i] = (CTd - self.CT) / delta
            dCQ_dr_fd[:, i] = (CQd - self.CQ) / delta
            dCM_dr_fd[:, i] = (CMd - self.CM) / delta
            dCP_dr_fd[:, i] = (CPd - self.CP) / delta

        np.testing.assert_allclose(dCT_dr_fd, dCT_dr, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCQ_dr_fd, dCQ_dr, rtol=3e-4, atol=1e-8)
        np.testing.assert_allclose(dCM_dr_fd, dCM_dr, rtol=3e-4, atol=1e-8)
        np.testing.assert_allclose(dCP_dr_fd, dCP_dr, rtol=3e-4, atol=1e-7)

    def test_dchord1(self):

        dNp_dchord = self.dNp["dchord"]
        dTp_dchord = self.dTp["dchord"]
        dNp_dchord_fd = np.zeros((self.n, self.n))
        dTp_dchord_fd = np.zeros((self.n, self.n))

        for i in range(self.n):
            chord = np.array(self.chord)
            delta = 1e-6 * chord[i]
            chord[i] += delta

            rotor = CCBlade(
                self.r,
                chord,
                self.theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                self.precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
            )

            loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
            Npd = loads["Np"]
            Tpd = loads["Tp"]

            dNp_dchord_fd[:, i] = (Npd - self.Np) / delta
            dTp_dchord_fd[:, i] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dchord_fd, dNp_dchord, rtol=1e-6, atol=1e-8)
        np.testing.assert_allclose(dTp_dchord_fd, dTp_dchord, rtol=5e-5, atol=1e-8)

    def test_dchord2(self):

        dT_dchord = self.dT["dchord"]
        dQ_dchord = self.dQ["dchord"]
        dM_dchord = self.dM["dchord"]
        dP_dchord = self.dP["dchord"]
        dT_dchord_fd = np.zeros((self.npts, self.n))
        dQ_dchord_fd = np.zeros((self.npts, self.n))
        dM_dchord_fd = np.zeros((self.npts, self.n))
        dP_dchord_fd = np.zeros((self.npts, self.n))

        for i in range(self.n):
            chord = np.array(self.chord)
            delta = 1e-6 * chord[i]
            chord[i] += delta

            rotor = CCBlade(
                self.r,
                chord,
                self.theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                self.precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
            )

            outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
            Pd = outputs["P"]
            Td = outputs["T"]
            Qd = outputs["Q"]
            Md = outputs["M"]

            dT_dchord_fd[:, i] = (Td - self.T) / delta
            dQ_dchord_fd[:, i] = (Qd - self.Q) / delta
            dM_dchord_fd[:, i] = (Md - self.M) / delta
            dP_dchord_fd[:, i] = (Pd - self.P) / delta

        np.testing.assert_allclose(dT_dchord_fd, dT_dchord, rtol=5e-6, atol=1e-8)
        np.testing.assert_allclose(dQ_dchord_fd, dQ_dchord, rtol=7e-5, atol=1e-8)
        np.testing.assert_allclose(dM_dchord_fd, dM_dchord, rtol=7e-5, atol=1e-8)
        np.testing.assert_allclose(dP_dchord_fd, dP_dchord, rtol=7e-5, atol=1e-8)

    def test_dchord3(self):

        dCT_dchord = self.dCT["dchord"]
        dCQ_dchord = self.dCQ["dchord"]
        dCM_dchord = self.dCM["dchord"]
        dCP_dchord = self.dCP["dchord"]
        dCT_dchord_fd = np.zeros((self.npts, self.n))
        dCQ_dchord_fd = np.zeros((self.npts, self.n))
        dCM_dchord_fd = np.zeros((self.npts, self.n))
        dCP_dchord_fd = np.zeros((self.npts, self.n))

        for i in range(self.n):
            chord = np.array(self.chord)
            delta = 1e-6 * chord[i]
            chord[i] += delta

            rotor = CCBlade(
                self.r,
                chord,
                self.theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                self.precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
            )

            outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
            CPd = outputs["CP"]
            CTd = outputs["CT"]
            CQd = outputs["CQ"]
            CMd = outputs["CM"]

            dCT_dchord_fd[:, i] = (CTd - self.CT) / delta
            dCQ_dchord_fd[:, i] = (CQd - self.CQ) / delta
            dCM_dchord_fd[:, i] = (CMd - self.CM) / delta
            dCP_dchord_fd[:, i] = (CPd - self.CP) / delta

        np.testing.assert_allclose(dCT_dchord_fd, dCT_dchord, rtol=5e-6, atol=1e-8)
        np.testing.assert_allclose(dCQ_dchord_fd, dCQ_dchord, rtol=7e-5, atol=1e-8)
        np.testing.assert_allclose(dCM_dchord_fd, dCM_dchord, rtol=7e-5, atol=1e-8)
        np.testing.assert_allclose(dCP_dchord_fd, dCP_dchord, rtol=7e-5, atol=1e-8)

    def test_dtheta1(self):

        dNp_dtheta = self.dNp["dtheta"]
        dTp_dtheta = self.dTp["dtheta"]
        dNp_dtheta_fd = np.zeros((self.n, self.n))
        dTp_dtheta_fd = np.zeros((self.n, self.n))

        for i in range(self.n):
            theta = np.array(self.theta)
            delta = 1e-6 * theta[i]
            theta[i] += delta

            rotor = CCBlade(
                self.r,
                self.chord,
                theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                self.precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
            )

            loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
            Npd = loads["Np"]
            Tpd = loads["Tp"]

            dNp_dtheta_fd[:, i] = (Npd - self.Np) / delta
            dTp_dtheta_fd[:, i] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dtheta_fd, dNp_dtheta, rtol=1e-6, atol=1e-8)
        np.testing.assert_allclose(dTp_dtheta_fd, dTp_dtheta, rtol=1e-4, atol=1e-8)

    def test_dtheta2(self):

        dT_dtheta = self.dT["dtheta"]
        dQ_dtheta = self.dQ["dtheta"]
        dM_dtheta = self.dM["dtheta"]
        dP_dtheta = self.dP["dtheta"]
        dT_dtheta_fd = np.zeros((self.npts, self.n))
        dQ_dtheta_fd = np.zeros((self.npts, self.n))
        dM_dtheta_fd = np.zeros((self.npts, self.n))
        dP_dtheta_fd = np.zeros((self.npts, self.n))

        for i in range(self.n):
            theta = np.array(self.theta)
            delta = 1e-6 * theta[i]
            theta[i] += delta

            rotor = CCBlade(
                self.r,
                self.chord,
                theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                self.precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
            )

            outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
            Pd = outputs["P"]
            Td = outputs["T"]
            Qd = outputs["Q"]
            Md = outputs["M"]

            dT_dtheta_fd[:, i] = (Td - self.T) / delta
            dQ_dtheta_fd[:, i] = (Qd - self.Q) / delta
            dM_dtheta_fd[:, i] = (Md - self.M) / delta
            dP_dtheta_fd[:, i] = (Pd - self.P) / delta

        np.testing.assert_allclose(dT_dtheta_fd, dT_dtheta, rtol=7e-5, atol=1e-8)
        np.testing.assert_allclose(dQ_dtheta_fd, dQ_dtheta, rtol=7e-5, atol=1e-8)
        np.testing.assert_allclose(dM_dtheta_fd, dM_dtheta, rtol=7e-5, atol=1e-8)
        np.testing.assert_allclose(dP_dtheta_fd, dP_dtheta, rtol=7e-5, atol=1e-8)

    def test_dtheta3(self):

        dCT_dtheta = self.dCT["dtheta"]
        dCQ_dtheta = self.dCQ["dtheta"]
        dCM_dtheta = self.dCM["dtheta"]
        dCP_dtheta = self.dCP["dtheta"]
        dCT_dtheta_fd = np.zeros((self.npts, self.n))
        dCQ_dtheta_fd = np.zeros((self.npts, self.n))
        dCM_dtheta_fd = np.zeros((self.npts, self.n))
        dCP_dtheta_fd = np.zeros((self.npts, self.n))

        for i in range(self.n):
            theta = np.array(self.theta)
            delta = 1e-6 * theta[i]
            theta[i] += delta

            rotor = CCBlade(
                self.r,
                self.chord,
                theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                self.precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
            )

            outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
            CPd = outputs["CP"]
            CTd = outputs["CT"]
            CQd = outputs["CQ"]
            CMd = outputs["CM"]

            dCT_dtheta_fd[:, i] = (CTd - self.CT) / delta
            dCQ_dtheta_fd[:, i] = (CQd - self.CQ) / delta
            dCM_dtheta_fd[:, i] = (CMd - self.CM) / delta
            dCP_dtheta_fd[:, i] = (CPd - self.CP) / delta

        np.testing.assert_allclose(dCT_dtheta_fd, dCT_dtheta, rtol=5e-6, atol=1e-8)
        np.testing.assert_allclose(dCQ_dtheta_fd, dCQ_dtheta, rtol=7e-5, atol=1e-8)
        np.testing.assert_allclose(dCM_dtheta_fd, dCM_dtheta, rtol=7e-5, atol=1e-8)
        np.testing.assert_allclose(dCP_dtheta_fd, dCP_dtheta, rtol=7e-5, atol=1e-8)

    def test_dRhub1(self):

        dNp_dRhub = self.dNp["dRhub"]
        dTp_dRhub = self.dTp["dRhub"]

        dNp_dRhub_fd = np.zeros((self.n, 1))
        dTp_dRhub_fd = np.zeros((self.n, 1))

        Rhub = float(self.Rhub)
        delta = 1e-6 * Rhub
        Rhub += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]

        dNp_dRhub_fd[:, 0] = (Npd - self.Np) / delta
        dTp_dRhub_fd[:, 0] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dRhub_fd, dNp_dRhub, rtol=1e-5, atol=1e-6)
        np.testing.assert_allclose(dTp_dRhub_fd, dTp_dRhub, rtol=1e-4, atol=1e-6)

    def test_dRhub2(self):

        dT_dRhub = self.dT["dRhub"]
        dQ_dRhub = self.dQ["dRhub"]
        dM_dRhub = self.dM["dRhub"]
        dP_dRhub = self.dP["dRhub"]

        dT_dRhub_fd = np.zeros((self.npts, 1))
        dQ_dRhub_fd = np.zeros((self.npts, 1))
        dM_dRhub_fd = np.zeros((self.npts, 1))
        dP_dRhub_fd = np.zeros((self.npts, 1))

        Rhub = float(self.Rhub)
        delta = 1e-6 * Rhub
        Rhub += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
        Pd = outputs["P"]
        Td = outputs["T"]
        Qd = outputs["Q"]
        Md = outputs["M"]

        dT_dRhub_fd[:, 0] = (Td - self.T) / delta
        dQ_dRhub_fd[:, 0] = (Qd - self.Q) / delta
        dM_dRhub_fd[:, 0] = (Md - self.M) / delta
        dP_dRhub_fd[:, 0] = (Pd - self.P) / delta

        np.testing.assert_allclose(dT_dRhub_fd, dT_dRhub, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dQ_dRhub_fd, dQ_dRhub, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dM_dRhub_fd, dM_dRhub, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dP_dRhub_fd, dP_dRhub, rtol=5e-5, atol=1e-8)

    def test_dRhub3(self):

        dCT_dRhub = self.dCT["dRhub"]
        dCQ_dRhub = self.dCQ["dRhub"]
        dCM_dRhub = self.dCM["dRhub"]
        dCP_dRhub = self.dCP["dRhub"]

        dCT_dRhub_fd = np.zeros((self.npts, 1))
        dCQ_dRhub_fd = np.zeros((self.npts, 1))
        dCM_dRhub_fd = np.zeros((self.npts, 1))
        dCP_dRhub_fd = np.zeros((self.npts, 1))

        Rhub = float(self.Rhub)
        delta = 1e-6 * Rhub
        Rhub += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
        CPd = outputs["CP"]
        CTd = outputs["CT"]
        CQd = outputs["CQ"]
        CMd = outputs["CM"]

        dCT_dRhub_fd[:, 0] = (CTd - self.CT) / delta
        dCQ_dRhub_fd[:, 0] = (CQd - self.CQ) / delta
        dCM_dRhub_fd[:, 0] = (CMd - self.CM) / delta
        dCP_dRhub_fd[:, 0] = (CPd - self.CP) / delta

        np.testing.assert_allclose(dCT_dRhub_fd, dCT_dRhub, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dCQ_dRhub_fd, dCQ_dRhub, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCM_dRhub_fd, dCM_dRhub, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCP_dRhub_fd, dCP_dRhub, rtol=5e-5, atol=1e-8)

    def test_dRtip1(self):

        dNp_dRtip = self.dNp["dRtip"]
        dTp_dRtip = self.dTp["dRtip"]

        dNp_dRtip_fd = np.zeros((self.n, 1))
        dTp_dRtip_fd = np.zeros((self.n, 1))

        Rtip = float(self.Rtip)
        delta = 1e-6 * Rtip
        Rtip += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]

        dNp_dRtip_fd[:, 0] = (Npd - self.Np) / delta
        dTp_dRtip_fd[:, 0] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dRtip_fd, dNp_dRtip, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dTp_dRtip_fd, dTp_dRtip, rtol=1e-4, atol=1e-8)

    def test_dRtip2(self):

        dT_dRtip = self.dT["dRtip"]
        dQ_dRtip = self.dQ["dRtip"]
        dM_dRtip = self.dM["dRtip"]
        dP_dRtip = self.dP["dRtip"]

        dT_dRtip_fd = np.zeros((self.npts, 1))
        dQ_dRtip_fd = np.zeros((self.npts, 1))
        dM_dRtip_fd = np.zeros((self.npts, 1))
        dP_dRtip_fd = np.zeros((self.npts, 1))

        Rtip = float(self.Rtip)
        delta = 1e-6 * Rtip
        Rtip += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
        Pd = outputs["P"]
        Td = outputs["T"]
        Qd = outputs["Q"]
        Md = outputs["M"]

        dT_dRtip_fd[:, 0] = (Td - self.T) / delta
        dQ_dRtip_fd[:, 0] = (Qd - self.Q) / delta
        dM_dRtip_fd[:, 0] = (Md - self.M) / delta
        dP_dRtip_fd[:, 0] = (Pd - self.P) / delta

        np.testing.assert_allclose(dT_dRtip_fd, dT_dRtip, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dQ_dRtip_fd, dQ_dRtip, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dM_dRtip_fd, dM_dRtip, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dP_dRtip_fd, dP_dRtip, rtol=5e-5, atol=1e-8)

    def test_dRtip3(self):

        dCT_dRtip = self.dCT["dRtip"]
        dCQ_dRtip = self.dCQ["dRtip"]
        dCM_dRtip = self.dCM["dRtip"]
        dCP_dRtip = self.dCP["dRtip"]

        dCT_dRtip_fd = np.zeros((self.npts, 1))
        dCQ_dRtip_fd = np.zeros((self.npts, 1))
        dCM_dRtip_fd = np.zeros((self.npts, 1))
        dCP_dRtip_fd = np.zeros((self.npts, 1))

        Rtip = float(self.Rtip)
        delta = 1e-6 * Rtip
        Rtip += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
        CPd = outputs["CP"]
        CTd = outputs["CT"]
        CQd = outputs["CQ"]
        CMd = outputs["CM"]

        dCT_dRtip_fd[:, 0] = (CTd - self.CT) / delta
        dCQ_dRtip_fd[:, 0] = (CQd - self.CQ) / delta
        dCM_dRtip_fd[:, 0] = (CMd - self.CM) / delta
        dCP_dRtip_fd[:, 0] = (CPd - self.CP) / delta

        np.testing.assert_allclose(dCT_dRtip_fd, dCT_dRtip, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dCQ_dRtip_fd, dCQ_dRtip, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCM_dRtip_fd, dCM_dRtip, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCP_dRtip_fd, dCP_dRtip, rtol=5e-5, atol=1e-8)

    def test_dprecone1(self):

        dNp_dprecone = self.dNp["dprecone"]
        dTp_dprecone = self.dTp["dprecone"]

        dNp_dprecone_fd = np.zeros((self.n, 1))
        dTp_dprecone_fd = np.zeros((self.n, 1))

        precone = float(self.precone)
        delta = 1e-6 * precone
        precone += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]

        dNp_dprecone_fd[:, 0] = (Npd - self.Np) / delta
        dTp_dprecone_fd[:, 0] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dprecone_fd, dNp_dprecone, rtol=1e-5, atol=1e-7)
        np.testing.assert_allclose(dTp_dprecone_fd, dTp_dprecone, rtol=1e-5, atol=1e-7)

    def test_dprecone2(self):

        dT_dprecone = self.dT["dprecone"]
        dQ_dprecone = self.dQ["dprecone"]
        dM_dprecone = self.dM["dprecone"]
        dP_dprecone = self.dP["dprecone"]

        dT_dprecone_fd = np.zeros((self.npts, 1))
        dQ_dprecone_fd = np.zeros((self.npts, 1))
        dM_dprecone_fd = np.zeros((self.npts, 1))
        dP_dprecone_fd = np.zeros((self.npts, 1))

        precone = float(self.precone)
        delta = 1e-6 * precone
        precone += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
        Pd = outputs["P"]
        Td = outputs["T"]
        Qd = outputs["Q"]
        Md = outputs["M"]

        dT_dprecone_fd[:, 0] = (Td - self.T) / delta
        dQ_dprecone_fd[:, 0] = (Qd - self.Q) / delta
        dM_dprecone_fd[:, 0] = (Md - self.M) / delta
        dP_dprecone_fd[:, 0] = (Pd - self.P) / delta

        np.testing.assert_allclose(dT_dprecone_fd, dT_dprecone, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dQ_dprecone_fd, dQ_dprecone, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dM_dprecone_fd, dM_dprecone, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dP_dprecone_fd, dP_dprecone, rtol=5e-5, atol=1e-8)

    def test_dprecone3(self):

        dCT_dprecone = self.dCT["dprecone"]
        dCQ_dprecone = self.dCQ["dprecone"]
        dCM_dprecone = self.dCM["dprecone"]
        dCP_dprecone = self.dCP["dprecone"]

        dCT_dprecone_fd = np.zeros((self.npts, 1))
        dCQ_dprecone_fd = np.zeros((self.npts, 1))
        dCM_dprecone_fd = np.zeros((self.npts, 1))
        dCP_dprecone_fd = np.zeros((self.npts, 1))

        precone = float(self.precone)
        delta = 1e-6 * precone
        precone += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
        CPd = outputs["CP"]
        CTd = outputs["CT"]
        CQd = outputs["CQ"]
        CMd = outputs["CM"]

        dCT_dprecone_fd[:, 0] = (CTd - self.CT) / delta
        dCQ_dprecone_fd[:, 0] = (CQd - self.CQ) / delta
        dCM_dprecone_fd[:, 0] = (CMd - self.CM) / delta
        dCP_dprecone_fd[:, 0] = (CPd - self.CP) / delta

        np.testing.assert_allclose(dCT_dprecone_fd, dCT_dprecone, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dCQ_dprecone_fd, dCQ_dprecone, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCM_dprecone_fd, dCM_dprecone, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCP_dprecone_fd, dCP_dprecone, rtol=5e-5, atol=1e-8)

    def test_dtilt1(self):

        dNp_dtilt = self.dNp["dtilt"]
        dTp_dtilt = self.dTp["dtilt"]

        dNp_dtilt_fd = np.zeros((self.n, 1))
        dTp_dtilt_fd = np.zeros((self.n, 1))

        tilt = float(self.tilt)
        delta = 1e-6 * tilt
        tilt += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]

        dNp_dtilt_fd[:, 0] = (Npd - self.Np) / delta
        dTp_dtilt_fd[:, 0] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dtilt_fd, dNp_dtilt, rtol=1e-6, atol=1e-8)
        np.testing.assert_allclose(dTp_dtilt_fd, dTp_dtilt, rtol=1e-5, atol=1e-8)

    def test_dtilt2(self):

        dT_dtilt = self.dT["dtilt"]
        dQ_dtilt = self.dQ["dtilt"]
        dM_dtilt = self.dM["dtilt"]
        dP_dtilt = self.dP["dtilt"]

        dT_dtilt_fd = np.zeros((self.npts, 1))
        dQ_dtilt_fd = np.zeros((self.npts, 1))
        dM_dtilt_fd = np.zeros((self.npts, 1))
        dP_dtilt_fd = np.zeros((self.npts, 1))

        tilt = float(self.tilt)
        delta = 1e-6 * tilt
        tilt += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
        Pd = outputs["P"]
        Td = outputs["T"]
        Qd = outputs["Q"]
        Md = outputs["M"]

        dT_dtilt_fd[:, 0] = (Td - self.T) / delta
        dQ_dtilt_fd[:, 0] = (Qd - self.Q) / delta
        dM_dtilt_fd[:, 0] = (Md - self.M) / delta
        dP_dtilt_fd[:, 0] = (Pd - self.P) / delta

        np.testing.assert_allclose(dT_dtilt_fd, dT_dtilt, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dQ_dtilt_fd, dQ_dtilt, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dM_dtilt_fd, dM_dtilt, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dP_dtilt_fd, dP_dtilt, rtol=5e-5, atol=1e-8)

    def test_dtilt3(self):

        dCT_dtilt = self.dCT["dtilt"]
        dCQ_dtilt = self.dCQ["dtilt"]
        dCM_dtilt = self.dCM["dtilt"]
        dCP_dtilt = self.dCP["dtilt"]

        dCT_dtilt_fd = np.zeros((self.npts, 1))
        dCQ_dtilt_fd = np.zeros((self.npts, 1))
        dCM_dtilt_fd = np.zeros((self.npts, 1))
        dCP_dtilt_fd = np.zeros((self.npts, 1))

        tilt = float(self.tilt)
        delta = 1e-6 * tilt
        tilt += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
        CPd = outputs["CP"]
        CTd = outputs["CT"]
        CQd = outputs["CQ"]
        CMd = outputs["CM"]

        dCT_dtilt_fd[:, 0] = (CTd - self.CT) / delta
        dCQ_dtilt_fd[:, 0] = (CQd - self.CQ) / delta
        dCM_dtilt_fd[:, 0] = (CMd - self.CM) / delta
        dCP_dtilt_fd[:, 0] = (CPd - self.CP) / delta

        np.testing.assert_allclose(dCT_dtilt_fd, dCT_dtilt, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dCQ_dtilt_fd, dCQ_dtilt, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCM_dtilt_fd, dCM_dtilt, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCP_dtilt_fd, dCP_dtilt, rtol=5e-5, atol=1e-8)

    def test_dhubht1(self):

        dNp_dhubht = self.dNp["dhubHt"]
        dTp_dhubht = self.dTp["dhubHt"]

        dNp_dhubht_fd = np.zeros((self.n, 1))
        dTp_dhubht_fd = np.zeros((self.n, 1))

        hubht = float(self.hubHt)
        delta = 1e-6 * hubht
        hubht += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            hubht,
            self.nSector,
            derivatives=False,
        )

        loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]

        dNp_dhubht_fd[:, 0] = (Npd - self.Np) / delta
        dTp_dhubht_fd[:, 0] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dhubht_fd, dNp_dhubht, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dTp_dhubht_fd, dTp_dhubht, rtol=1e-5, atol=1e-8)

    def test_dhubht2(self):

        dT_dhubht = self.dT["dhubHt"]
        dQ_dhubht = self.dQ["dhubHt"]
        dM_dhubht = self.dM["dhubHt"]
        dP_dhubht = self.dP["dhubHt"]

        dT_dhubht_fd = np.zeros((self.npts, 1))
        dQ_dhubht_fd = np.zeros((self.npts, 1))
        dM_dhubht_fd = np.zeros((self.npts, 1))
        dP_dhubht_fd = np.zeros((self.npts, 1))

        hubht = float(self.hubHt)
        delta = 1e-6 * hubht
        hubht += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            hubht,
            self.nSector,
            derivatives=False,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
        Pd = outputs["P"]
        Td = outputs["T"]
        Qd = outputs["Q"]
        Md = outputs["M"]

        dT_dhubht_fd[:, 0] = (Td - self.T) / delta
        dQ_dhubht_fd[:, 0] = (Qd - self.Q) / delta
        dM_dhubht_fd[:, 0] = (Md - self.M) / delta
        dP_dhubht_fd[:, 0] = (Pd - self.P) / delta

        np.testing.assert_allclose(dT_dhubht_fd, dT_dhubht, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dQ_dhubht_fd, dQ_dhubht, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dM_dhubht_fd, dM_dhubht, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dP_dhubht_fd, dP_dhubht, rtol=5e-5, atol=1e-8)

    def test_dhubht3(self):

        dCT_dhubht = self.dCT["dhubHt"]
        dCQ_dhubht = self.dCQ["dhubHt"]
        dCM_dhubht = self.dCM["dhubHt"]
        dCP_dhubht = self.dCP["dhubHt"]

        dCT_dhubht_fd = np.zeros((self.npts, 1))
        dCQ_dhubht_fd = np.zeros((self.npts, 1))
        dCM_dhubht_fd = np.zeros((self.npts, 1))
        dCP_dhubht_fd = np.zeros((self.npts, 1))

        hubht = float(self.hubHt)
        delta = 1e-6 * hubht
        hubht += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            hubht,
            self.nSector,
            derivatives=False,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
        CPd = outputs["CP"]
        CTd = outputs["CT"]
        CQd = outputs["CQ"]
        CMd = outputs["CM"]

        dCT_dhubht_fd[:, 0] = (CTd - self.CT) / delta
        dCQ_dhubht_fd[:, 0] = (CQd - self.CQ) / delta
        dCM_dhubht_fd[:, 0] = (CMd - self.CM) / delta
        dCP_dhubht_fd[:, 0] = (CPd - self.CP) / delta

        np.testing.assert_allclose(dCT_dhubht_fd, dCT_dhubht, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dCQ_dhubht_fd, dCQ_dhubht, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCM_dhubht_fd, dCM_dhubht, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCP_dhubht_fd, dCP_dhubht, rtol=5e-5, atol=1e-8)

    def test_dyaw1(self):

        dNp_dyaw = self.dNp["dyaw"]
        dTp_dyaw = self.dTp["dyaw"]

        dNp_dyaw_fd = np.zeros((self.n, 1))
        dTp_dyaw_fd = np.zeros((self.n, 1))

        yaw = float(self.yaw)
        delta = 1e-6
        yaw += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]

        dNp_dyaw_fd[:, 0] = (Npd - self.Np) / delta
        dTp_dyaw_fd[:, 0] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dyaw_fd, dNp_dyaw, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dTp_dyaw_fd, dTp_dyaw, rtol=1e-5, atol=1e-8)

    def test_dyaw2(self):

        dT_dyaw = self.dT["dyaw"]
        dQ_dyaw = self.dQ["dyaw"]
        dM_dyaw = self.dM["dyaw"]
        dP_dyaw = self.dP["dyaw"]

        dT_dyaw_fd = np.zeros((self.npts, 1))
        dQ_dyaw_fd = np.zeros((self.npts, 1))
        dM_dyaw_fd = np.zeros((self.npts, 1))
        dP_dyaw_fd = np.zeros((self.npts, 1))

        yaw = float(self.yaw)
        delta = 1e-6
        yaw += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
        Pd = outputs["P"]
        Td = outputs["T"]
        Qd = outputs["Q"]
        Md = outputs["M"]

        dT_dyaw_fd[:, 0] = (Td - self.T) / delta
        dQ_dyaw_fd[:, 0] = (Qd - self.Q) / delta
        dM_dyaw_fd[:, 0] = (Md - self.M) / delta
        dP_dyaw_fd[:, 0] = (Pd - self.P) / delta

        np.testing.assert_allclose(dT_dyaw_fd, dT_dyaw, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dQ_dyaw_fd, dQ_dyaw, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dM_dyaw_fd, dM_dyaw, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dP_dyaw_fd, dP_dyaw, rtol=5e-5, atol=1e-8)

    def test_dyaw3(self):

        dCT_dyaw = self.dCT["dyaw"]
        dCQ_dyaw = self.dCQ["dyaw"]
        dCM_dyaw = self.dCM["dyaw"]
        dCP_dyaw = self.dCP["dyaw"]

        dCT_dyaw_fd = np.zeros((self.npts, 1))
        dCQ_dyaw_fd = np.zeros((self.npts, 1))
        dCM_dyaw_fd = np.zeros((self.npts, 1))
        dCP_dyaw_fd = np.zeros((self.npts, 1))

        yaw = float(self.yaw)
        delta = 1e-6
        yaw += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
        CPd = outputs["CP"]
        CTd = outputs["CT"]
        CQd = outputs["CQ"]
        CMd = outputs["CM"]

        dCT_dyaw_fd[:, 0] = (CTd - self.CT) / delta
        dCQ_dyaw_fd[:, 0] = (CQd - self.CQ) / delta
        dCM_dyaw_fd[:, 0] = (CMd - self.CM) / delta
        dCP_dyaw_fd[:, 0] = (CPd - self.CP) / delta

        np.testing.assert_allclose(dCT_dyaw_fd, dCT_dyaw, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dCQ_dyaw_fd, dCQ_dyaw, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCM_dyaw_fd, dCM_dyaw, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCP_dyaw_fd, dCP_dyaw, rtol=5e-5, atol=1e-8)

    def test_dshear1(self):

        dNp_dshear = self.dNp["dshear"]
        dTp_dshear = self.dTp["dshear"]

        dNp_dshear_fd = np.zeros((self.n, 1))
        dTp_dshear_fd = np.zeros((self.n, 1))

        shearExp = float(self.shearExp)
        delta = 1e-6
        shearExp += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]

        dNp_dshear_fd[:, 0] = (Npd - self.Np) / delta
        dTp_dshear_fd[:, 0] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dshear_fd, dNp_dshear, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dTp_dshear_fd, dTp_dshear, rtol=1e-5, atol=1e-8)

    def test_dshear2(self):

        dT_dshear = self.dT["dshear"]
        dQ_dshear = self.dQ["dshear"]
        dM_dshear = self.dM["dshear"]
        dP_dshear = self.dP["dshear"]

        dT_dshear_fd = np.zeros((self.npts, 1))
        dQ_dshear_fd = np.zeros((self.npts, 1))
        dM_dshear_fd = np.zeros((self.npts, 1))
        dP_dshear_fd = np.zeros((self.npts, 1))

        shearExp = float(self.shearExp)
        delta = 1e-6
        shearExp += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
        Pd = outputs["P"]
        Td = outputs["T"]
        Qd = outputs["Q"]
        Md = outputs["M"]

        dT_dshear_fd[:, 0] = (Td - self.T) / delta
        dQ_dshear_fd[:, 0] = (Qd - self.Q) / delta
        dM_dshear_fd[:, 0] = (Md - self.M) / delta
        dP_dshear_fd[:, 0] = (Pd - self.P) / delta

        np.testing.assert_allclose(dT_dshear_fd, dT_dshear, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dQ_dshear_fd, dQ_dshear, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dM_dshear_fd, dM_dshear, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dP_dshear_fd, dP_dshear, rtol=5e-5, atol=1e-8)

    def test_dshear3(self):

        dCT_dshear = self.dCT["dshear"]
        dCQ_dshear = self.dCQ["dshear"]
        dCM_dshear = self.dCM["dshear"]
        dCP_dshear = self.dCP["dshear"]

        dCT_dshear_fd = np.zeros((self.npts, 1))
        dCQ_dshear_fd = np.zeros((self.npts, 1))
        dCM_dshear_fd = np.zeros((self.npts, 1))
        dCP_dshear_fd = np.zeros((self.npts, 1))

        shearExp = float(self.shearExp)
        delta = 1e-6
        shearExp += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            self.precone,
            self.tilt,
            self.yaw,
            shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
        CPd = outputs["CP"]
        CTd = outputs["CT"]
        CQd = outputs["CQ"]
        CMd = outputs["CM"]

        dCT_dshear_fd[:, 0] = (CTd - self.CT) / delta
        dCQ_dshear_fd[:, 0] = (CQd - self.CQ) / delta
        dCM_dshear_fd[:, 0] = (CMd - self.CM) / delta
        dCP_dshear_fd[:, 0] = (CPd - self.CP) / delta

        np.testing.assert_allclose(dCT_dshear_fd, dCT_dshear, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dCQ_dshear_fd, dCQ_dshear, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCM_dshear_fd, dCM_dshear, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCP_dshear_fd, dCP_dshear, rtol=5e-5, atol=1e-8)

    def test_dazimuth1(self):

        dNp_dazimuth = self.dNp["dazimuth"]
        dTp_dazimuth = self.dTp["dazimuth"]

        dNp_dazimuth_fd = np.zeros((self.n, 1))
        dTp_dazimuth_fd = np.zeros((self.n, 1))

        azimuth = float(self.azimuth)
        delta = 1e-6 * azimuth
        azimuth += delta

        outputs, _ = self.rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, azimuth)
        Npd = outputs["Np"]
        Tpd = outputs["Tp"]

        dNp_dazimuth_fd[:, 0] = (Npd - self.Np) / delta
        dTp_dazimuth_fd[:, 0] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dazimuth_fd, dNp_dazimuth, rtol=1e-5, atol=1e-6)
        np.testing.assert_allclose(dTp_dazimuth_fd, dTp_dazimuth, rtol=1e-5, atol=1e-6)

    def test_dUinf1(self):

        dNp_dUinf = self.dNp["dUinf"]
        dTp_dUinf = self.dTp["dUinf"]

        dNp_dUinf_fd = np.zeros((self.n, 1))
        dTp_dUinf_fd = np.zeros((self.n, 1))

        Uinf = float(self.Uinf)
        delta = 1e-6 * Uinf
        Uinf += delta

        outputs, _ = self.rotor.distributedAeroLoads(Uinf, self.Omega, self.pitch, self.azimuth)
        Npd = outputs["Np"]
        Tpd = outputs["Tp"]

        dNp_dUinf_fd[:, 0] = (Npd - self.Np) / delta
        dTp_dUinf_fd[:, 0] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dUinf_fd, dNp_dUinf, rtol=1e-5, atol=1e-6)
        np.testing.assert_allclose(dTp_dUinf_fd, dTp_dUinf, rtol=1e-5, atol=1e-6)

    def test_dUinf2(self):

        dT_dUinf = self.dT["dUinf"]
        dQ_dUinf = self.dQ["dUinf"]
        dM_dUinf = self.dM["dUinf"]
        dP_dUinf = self.dP["dUinf"]

        dT_dUinf_fd = np.zeros((self.npts, self.npts))
        dQ_dUinf_fd = np.zeros((self.npts, self.npts))
        dM_dUinf_fd = np.zeros((self.npts, self.npts))
        dP_dUinf_fd = np.zeros((self.npts, self.npts))

        Uinf = float(self.Uinf)
        delta = 1e-6 * Uinf
        Uinf += delta

        outputs, _ = self.rotor.evaluate([Uinf], [self.Omega], [self.pitch], coefficients=False)
        Pd = outputs["P"]
        Td = outputs["T"]
        Qd = outputs["Q"]
        Md = outputs["M"]

        dT_dUinf_fd[:, 0] = (Td - self.T) / delta
        dQ_dUinf_fd[:, 0] = (Qd - self.Q) / delta
        dM_dUinf_fd[:, 0] = (Md - self.M) / delta
        dP_dUinf_fd[:, 0] = (Pd - self.P) / delta

        np.testing.assert_allclose(dT_dUinf_fd, dT_dUinf, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dQ_dUinf_fd, dQ_dUinf, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dM_dUinf_fd, dM_dUinf, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dP_dUinf_fd, dP_dUinf, rtol=5e-5, atol=1e-8)

    def test_dUinf3(self):

        dCT_dUinf = self.dCT["dUinf"]
        dCQ_dUinf = self.dCQ["dUinf"]
        dCM_dUinf = self.dCM["dUinf"]
        dCP_dUinf = self.dCP["dUinf"]

        dCT_dUinf_fd = np.zeros((self.npts, self.npts))
        dCQ_dUinf_fd = np.zeros((self.npts, self.npts))
        dCM_dUinf_fd = np.zeros((self.npts, self.npts))
        dCP_dUinf_fd = np.zeros((self.npts, self.npts))

        Uinf = float(self.Uinf)
        delta = 1e-6 * Uinf
        Uinf += delta

        outputs, _ = self.rotor.evaluate([Uinf], [self.Omega], [self.pitch], coefficients=True)
        CPd = outputs["CP"]
        CTd = outputs["CT"]
        CQd = outputs["CQ"]
        CMd = outputs["CM"]

        dCT_dUinf_fd[:, 0] = (CTd - self.CT) / delta
        dCQ_dUinf_fd[:, 0] = (CQd - self.CQ) / delta
        dCM_dUinf_fd[:, 0] = (CMd - self.CM) / delta
        dCP_dUinf_fd[:, 0] = (CPd - self.CP) / delta

        np.testing.assert_allclose(dCT_dUinf_fd, dCT_dUinf, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dCQ_dUinf_fd, dCQ_dUinf, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCM_dUinf_fd, dCM_dUinf, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCP_dUinf_fd, dCP_dUinf, rtol=5e-5, atol=1e-8)

    def test_dOmega1(self):

        dNp_dOmega = self.dNp["dOmega"]
        dTp_dOmega = self.dTp["dOmega"]

        dNp_dOmega_fd = np.zeros((self.n, 1))
        dTp_dOmega_fd = np.zeros((self.n, 1))

        Omega = float(self.Omega)
        delta = 1e-6 * Omega
        Omega += delta

        loads, _ = self.rotor.distributedAeroLoads(self.Uinf, Omega, self.pitch, self.azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]

        dNp_dOmega_fd[:, 0] = (Npd - self.Np) / delta
        dTp_dOmega_fd[:, 0] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dOmega_fd, dNp_dOmega, rtol=1e-5, atol=1e-6)
        np.testing.assert_allclose(dTp_dOmega_fd, dTp_dOmega, rtol=1e-5, atol=1e-6)

    def test_dOmega2(self):

        dT_dOmega = self.dT["dOmega"]
        dQ_dOmega = self.dQ["dOmega"]
        dM_dOmega = self.dM["dOmega"]
        dP_dOmega = self.dP["dOmega"]

        dT_dOmega_fd = np.zeros((self.npts, self.npts))
        dQ_dOmega_fd = np.zeros((self.npts, self.npts))
        dM_dOmega_fd = np.zeros((self.npts, self.npts))
        dP_dOmega_fd = np.zeros((self.npts, self.npts))

        Omega = float(self.Omega)
        delta = 1e-6 * Omega
        Omega += delta

        outputs, _ = self.rotor.evaluate([self.Uinf], [Omega], [self.pitch], coefficients=False)
        Pd = outputs["P"]
        Td = outputs["T"]
        Qd = outputs["Q"]
        Md = outputs["M"]

        dT_dOmega_fd[:, 0] = (Td - self.T) / delta
        dQ_dOmega_fd[:, 0] = (Qd - self.Q) / delta
        dM_dOmega_fd[:, 0] = (Md - self.M) / delta
        dP_dOmega_fd[:, 0] = (Pd - self.P) / delta

        np.testing.assert_allclose(dT_dOmega_fd, dT_dOmega, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dQ_dOmega_fd, dQ_dOmega, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dM_dOmega_fd, dM_dOmega, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dP_dOmega_fd, dP_dOmega, rtol=5e-5, atol=1e-8)

    def test_dOmega3(self):

        dCT_dOmega = self.dCT["dOmega"]
        dCQ_dOmega = self.dCQ["dOmega"]
        dCM_dOmega = self.dCM["dOmega"]
        dCP_dOmega = self.dCP["dOmega"]

        dCT_dOmega_fd = np.zeros((self.npts, self.npts))
        dCQ_dOmega_fd = np.zeros((self.npts, self.npts))
        dCM_dOmega_fd = np.zeros((self.npts, self.npts))
        dCP_dOmega_fd = np.zeros((self.npts, self.npts))

        Omega = float(self.Omega)
        delta = 1e-6 * Omega
        Omega += delta

        outputs, _ = self.rotor.evaluate([self.Uinf], [Omega], [self.pitch], coefficients=True)
        CPd = outputs["CP"]
        CTd = outputs["CT"]
        CQd = outputs["CQ"]
        CMd = outputs["CM"]

        dCT_dOmega_fd[:, 0] = (CTd - self.CT) / delta
        dCQ_dOmega_fd[:, 0] = (CQd - self.CQ) / delta
        dCM_dOmega_fd[:, 0] = (CMd - self.CM) / delta
        dCP_dOmega_fd[:, 0] = (CPd - self.CP) / delta

        np.testing.assert_allclose(dCT_dOmega_fd, dCT_dOmega, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dCQ_dOmega_fd, dCQ_dOmega, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCM_dOmega_fd, dCM_dOmega, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCP_dOmega_fd, dCP_dOmega, rtol=5e-5, atol=1e-8)

    def test_dpitch1(self):

        dNp_dpitch = self.dNp["dpitch"]
        dTp_dpitch = self.dTp["dpitch"]

        dNp_dpitch_fd = np.zeros((self.n, 1))
        dTp_dpitch_fd = np.zeros((self.n, 1))

        pitch = float(self.pitch)
        delta = 1e-6
        pitch += delta

        loads, _ = self.rotor.distributedAeroLoads(self.Uinf, self.Omega, pitch, self.azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]

        dNp_dpitch_fd[:, 0] = (Npd - self.Np) / delta
        dTp_dpitch_fd[:, 0] = (Tpd - self.Tp) / delta

        np.testing.assert_allclose(dNp_dpitch_fd, dNp_dpitch, rtol=5e-5, atol=1e-6)
        np.testing.assert_allclose(dTp_dpitch_fd, dTp_dpitch, rtol=5e-5, atol=1e-6)

    def test_dpitch2(self):

        dT_dpitch = self.dT["dpitch"]
        dQ_dpitch = self.dQ["dpitch"]
        dM_dpitch = self.dM["dpitch"]
        dP_dpitch = self.dP["dpitch"]

        dT_dpitch_fd = np.zeros((self.npts, 1))
        dQ_dpitch_fd = np.zeros((self.npts, 1))
        dM_dpitch_fd = np.zeros((self.npts, 1))
        dP_dpitch_fd = np.zeros((self.npts, 1))

        pitch = float(self.pitch)
        delta = 1e-6
        pitch += delta

        outputs, _ = self.rotor.evaluate([self.Uinf], [self.Omega], [pitch], coefficients=False)
        Pd = outputs["P"]
        Td = outputs["T"]
        Qd = outputs["Q"]
        Md = outputs["M"]

        dT_dpitch_fd[:, 0] = (Td - self.T) / delta
        dQ_dpitch_fd[:, 0] = (Qd - self.Q) / delta
        dM_dpitch_fd[:, 0] = (Md - self.M) / delta
        dP_dpitch_fd[:, 0] = (Pd - self.P) / delta

        np.testing.assert_allclose(dT_dpitch_fd, dT_dpitch, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dQ_dpitch_fd, dQ_dpitch, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dM_dpitch_fd, dM_dpitch, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dP_dpitch_fd, dP_dpitch, rtol=5e-5, atol=1e-8)

    def test_dpitch3(self):

        dCT_dpitch = self.dCT["dpitch"]
        dCQ_dpitch = self.dCQ["dpitch"]
        dCM_dpitch = self.dCM["dpitch"]
        dCP_dpitch = self.dCP["dpitch"]

        dCT_dpitch_fd = np.zeros((self.npts, 1))
        dCQ_dpitch_fd = np.zeros((self.npts, 1))
        dCM_dpitch_fd = np.zeros((self.npts, 1))
        dCP_dpitch_fd = np.zeros((self.npts, 1))

        pitch = float(self.pitch)
        delta = 1e-6
        pitch += delta

        outputs, _ = self.rotor.evaluate([self.Uinf], [self.Omega], [pitch], coefficients=True)
        CPd = outputs["CP"]
        CTd = outputs["CT"]
        CQd = outputs["CQ"]
        CMd = outputs["CM"]

        dCT_dpitch_fd[:, 0] = (CTd - self.CT) / delta
        dCQ_dpitch_fd[:, 0] = (CQd - self.CQ) / delta
        dCM_dpitch_fd[:, 0] = (CMd - self.CM) / delta
        dCP_dpitch_fd[:, 0] = (CPd - self.CP) / delta

        np.testing.assert_allclose(dCT_dpitch_fd, dCT_dpitch, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dCQ_dpitch_fd, dCQ_dpitch, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCM_dpitch_fd, dCM_dpitch, rtol=5e-5, atol=1e-8)
        np.testing.assert_allclose(dCP_dpitch_fd, dCP_dpitch, rtol=5e-5, atol=1e-8)

    def test_dprecurve1(self):

        precurve = np.linspace(1, 10, self.n)
        precurveTip = precurve[-1]
        precone = 0.0
        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=True,
            precurve=precurve,
            precurveTip=precurveTip,
        )
        precurve = rotor.precurve.copy()

        loads, derivs = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Np = loads["Np"]
        Tp = loads["Tp"]
        dNp = derivs["dNp"]
        dTp = derivs["dTp"]

        dNp_dprecurve = dNp["dprecurve"]
        dTp_dprecurve = dTp["dprecurve"]

        dNp_dprecurve_fd = np.zeros((self.n, self.n))
        dTp_dprecurve_fd = np.zeros((self.n, self.n))

        for i in range(self.n):
            pc = np.array(precurve)
            delta = 1e-6 * pc[i]
            pc[i] += delta

            rotor = CCBlade(
                self.r,
                self.chord,
                self.theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
                precurve=pc,
                precurveTip=precurveTip,
            )

            loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
            Npd = loads["Np"]
            Tpd = loads["Tp"]

            dNp_dprecurve_fd[:, i] = (Npd - Np) / delta
            dTp_dprecurve_fd[:, i] = (Tpd - Tp) / delta

        np.testing.assert_allclose(dNp_dprecurve_fd, dNp_dprecurve, rtol=3e-4, atol=1e-8)
        np.testing.assert_allclose(dTp_dprecurve_fd, dTp_dprecurve, rtol=3e-4, atol=1e-8)

    def test_dprecurve2(self):

        precurve = np.linspace(1, 10, self.n)
        precurveTip = precurve[-1]
        precone = 0.0
        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=True,
            precurve=precurve,
            precurveTip=precurveTip,
        )
        precurve = rotor.precurve.copy()

        outputs, derivs = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
        P = outputs["P"]
        T = outputs["T"]
        Q = outputs["Q"]
        M = outputs["M"]
        dP = derivs["dP"]
        dT = derivs["dT"]
        dQ = derivs["dQ"]
        dM = derivs["dM"]

        dT_dprecurve = dT["dprecurve"]
        dQ_dprecurve = dQ["dprecurve"]
        dM_dprecurve = dM["dprecurve"]
        dP_dprecurve = dP["dprecurve"]

        dT_dprecurve_fd = np.zeros((self.npts, self.n))
        dQ_dprecurve_fd = np.zeros((self.npts, self.n))
        dM_dprecurve_fd = np.zeros((self.npts, self.n))
        dP_dprecurve_fd = np.zeros((self.npts, self.n))
        for i in range(self.n):
            pc = np.array(precurve)
            delta = 1e-6 * pc[i]
            pc[i] += delta

            rotor = CCBlade(
                self.r,
                self.chord,
                self.theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
                precurve=pc,
                precurveTip=precurveTip,
            )

            outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
            Pd = outputs["P"]
            Td = outputs["T"]
            Qd = outputs["Q"]
            Md = outputs["M"]

            dT_dprecurve_fd[:, i] = (Td - T) / delta
            dQ_dprecurve_fd[:, i] = (Qd - Q) / delta
            dM_dprecurve_fd[:, i] = (Md - M) / delta
            dP_dprecurve_fd[:, i] = (Pd - P) / delta

        np.testing.assert_allclose(dT_dprecurve_fd, dT_dprecurve, rtol=3e-4, atol=1e-8)
        np.testing.assert_allclose(dQ_dprecurve_fd, dQ_dprecurve, rtol=3e-4, atol=1e-8)
        np.testing.assert_allclose(dM_dprecurve_fd, dM_dprecurve, rtol=8e-4, atol=1e-8)
        np.testing.assert_allclose(dP_dprecurve_fd, dP_dprecurve, rtol=3e-4, atol=1e-8)

    def test_dprecurve3(self):

        precurve = np.linspace(1, 10, self.n)
        precurveTip = precurve[-1]
        precone = 0.0
        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=True,
            precurve=precurve,
            precurveTip=precurveTip,
        )
        precurve = rotor.precurve.copy()

        outputs, derivs = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
        CP = outputs["CP"]
        CT = outputs["CT"]
        CQ = outputs["CQ"]
        CM = outputs["CM"]
        dCP = derivs["dCP"]
        dCT = derivs["dCT"]
        dCQ = derivs["dCQ"]
        dCM = derivs["dCM"]

        dCT_dprecurve = dCT["dprecurve"]
        dCQ_dprecurve = dCQ["dprecurve"]
        dCM_dprecurve = dCM["dprecurve"]
        dCP_dprecurve = dCP["dprecurve"]

        dCT_dprecurve_fd = np.zeros((self.npts, self.n))
        dCQ_dprecurve_fd = np.zeros((self.npts, self.n))
        dCM_dprecurve_fd = np.zeros((self.npts, self.n))
        dCP_dprecurve_fd = np.zeros((self.npts, self.n))
        for i in range(self.n):
            pc = np.array(precurve)
            delta = 1e-6 * pc[i]
            pc[i] += delta

            rotor = CCBlade(
                self.r,
                self.chord,
                self.theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
                precurve=pc,
                precurveTip=precurveTip,
            )

            outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
            CPd = outputs["CP"]
            CTd = outputs["CT"]
            CQd = outputs["CQ"]
            CMd = outputs["CM"]

            dCT_dprecurve_fd[:, i] = (CTd - CT) / delta
            dCQ_dprecurve_fd[:, i] = (CQd - CQ) / delta
            dCM_dprecurve_fd[:, i] = (CMd - CM) / delta
            dCP_dprecurve_fd[:, i] = (CPd - CP) / delta

        np.testing.assert_allclose(dCT_dprecurve_fd, dCT_dprecurve, rtol=3e-4, atol=1e-8)
        np.testing.assert_allclose(dCQ_dprecurve_fd, dCQ_dprecurve, rtol=3e-4, atol=1e-8)
        np.testing.assert_allclose(dCM_dprecurve_fd, dCM_dprecurve, rtol=3e-4, atol=1e-8)
        np.testing.assert_allclose(dCP_dprecurve_fd, dCP_dprecurve, rtol=3e-4, atol=1e-8)

    def test_dpresweep1(self):

        presweep = np.linspace(1, 10, self.n)
        presweepTip = presweep[-1]
        precone = 0.0
        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=True,
            presweep=presweep,
            presweepTip=presweepTip,
        )
        presweep = rotor.presweep.copy()

        loads, derivs = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Np = loads["Np"]
        Tp = loads["Tp"]
        dNp = derivs["dNp"]
        dTp = derivs["dTp"]

        dNp_dpresweep = dNp["dpresweep"]
        dTp_dpresweep = dTp["dpresweep"]

        dNp_dpresweep_fd = np.zeros((self.n, self.n))
        dTp_dpresweep_fd = np.zeros((self.n, self.n))

        for i in range(self.n):
            ps = np.array(presweep)
            delta = 1e-6 * ps[i]
            ps[i] += delta

            rotor = CCBlade(
                self.r,
                self.chord,
                self.theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
                presweep=ps,
                presweepTip=presweepTip,
            )

            loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
            Npd = loads["Np"]
            Tpd = loads["Tp"]

            dNp_dpresweep_fd[:, i] = (Npd - Np) / delta
            dTp_dpresweep_fd[:, i] = (Tpd - Tp) / delta

        np.testing.assert_allclose(dNp_dpresweep_fd, dNp_dpresweep, rtol=1e-5, atol=1e-8)
        np.testing.assert_allclose(dTp_dpresweep_fd, dTp_dpresweep, rtol=1e-5, atol=1e-8)

    def test_dpresweep2(self):

        presweep = np.linspace(1, 10, self.n)
        presweepTip = presweep[-1]
        precone = 0.0
        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=True,
            presweep=presweep,
            presweepTip=presweepTip,
        )
        presweep = rotor.presweep.copy()

        outputs, derivs = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
        P = outputs["P"]
        T = outputs["T"]
        Q = outputs["Q"]
        M = outputs["M"]
        dP = derivs["dP"]
        dT = derivs["dT"]
        dQ = derivs["dQ"]
        dM = derivs["dM"]

        dT_dpresweep = dT["dpresweep"]
        dQ_dpresweep = dQ["dpresweep"]
        dM_dpresweep = dM["dpresweep"]
        dP_dpresweep = dP["dpresweep"]

        dT_dpresweep_fd = np.zeros((self.npts, self.n))
        dQ_dpresweep_fd = np.zeros((self.npts, self.n))
        dM_dpresweep_fd = np.zeros((self.npts, self.n))
        dP_dpresweep_fd = np.zeros((self.npts, self.n))
        for i in range(self.n):
            ps = np.array(presweep)
            delta = 1e-6 * ps[i]
            ps[i] += delta

            rotor = CCBlade(
                self.r,
                self.chord,
                self.theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
                presweep=ps,
                presweepTip=presweepTip,
            )

            outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
            Pd = outputs["P"]
            Td = outputs["T"]
            Qd = outputs["Q"]
            Md = outputs["M"]

            dT_dpresweep_fd[:, i] = (Td - T) / delta
            dQ_dpresweep_fd[:, i] = (Qd - Q) / delta
            dM_dpresweep_fd[:, i] = (Md - M) / delta
            dP_dpresweep_fd[:, i] = (Pd - P) / delta

        np.testing.assert_allclose(dT_dpresweep_fd, dT_dpresweep, rtol=3e-4, atol=1e-8)
        np.testing.assert_allclose(dQ_dpresweep_fd, dQ_dpresweep, rtol=3e-4, atol=1e-8)
        np.testing.assert_allclose(dM_dpresweep_fd, dM_dpresweep, rtol=3e-4, atol=1e-8)
        np.testing.assert_allclose(dP_dpresweep_fd, dP_dpresweep, rtol=3e-4, atol=1e-8)

    def test_dpresweep3(self):

        presweep = np.linspace(1, 10, self.n)
        presweepTip = presweep[-1]
        precone = 0.0
        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=True,
            presweep=presweep,
            presweepTip=presweepTip,
        )
        presweep = rotor.presweep.copy()

        outputs, derivs = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
        CP = outputs["CP"]
        CT = outputs["CT"]
        CQ = outputs["CQ"]
        CM = outputs["CM"]
        dCP = derivs["dCP"]
        dCT = derivs["dCT"]
        dCQ = derivs["dCQ"]
        dCM = derivs["dCM"]

        dCT_dpresweep = dCT["dpresweep"]
        dCQ_dpresweep = dCQ["dpresweep"]
        dCM_dpresweep = dCM["dpresweep"]
        dCP_dpresweep = dCP["dpresweep"]

        dCT_dpresweep_fd = np.zeros((self.npts, self.n))
        dCQ_dpresweep_fd = np.zeros((self.npts, self.n))
        dCM_dpresweep_fd = np.zeros((self.npts, self.n))
        dCP_dpresweep_fd = np.zeros((self.npts, self.n))
        for i in range(self.n):
            ps = np.array(presweep)
            delta = 1e-6 * ps[i]
            ps[i] += delta

            rotor = CCBlade(
                self.r,
                self.chord,
                self.theta,
                self.af,
                self.Rhub,
                self.Rtip,
                self.B,
                self.rho,
                self.mu,
                precone,
                self.tilt,
                self.yaw,
                self.shearExp,
                self.hubHt,
                self.nSector,
                derivatives=False,
                presweep=ps,
                presweepTip=presweepTip,
            )

            outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
            CPd = outputs["CP"]
            CTd = outputs["CT"]
            CQd = outputs["CQ"]
            CMd = outputs["CM"]

            dCT_dpresweep_fd[:, i] = (CTd - CT) / delta
            dCQ_dpresweep_fd[:, i] = (CQd - CQ) / delta
            dCM_dpresweep_fd[:, i] = (CMd - CM) / delta
            dCP_dpresweep_fd[:, i] = (CPd - CP) / delta

        np.testing.assert_allclose(dCT_dpresweep_fd, dCT_dpresweep, rtol=3e-4, atol=1e-8)
        np.testing.assert_allclose(dCQ_dpresweep_fd, dCQ_dpresweep, rtol=3e-4, atol=1e-8)
        np.testing.assert_allclose(dCM_dpresweep_fd, dCM_dpresweep, rtol=3e-4, atol=1e-8)
        np.testing.assert_allclose(dCP_dpresweep_fd, dCP_dpresweep, rtol=3e-4, atol=1e-8)

    def test_dprecurveTip1(self):

        precurve = np.linspace(1, 10, self.n)
        precurveTip = precurve[-1]
        precone = 0.0
        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=True,
            precurve=precurve,
            precurveTip=precurveTip,
        )

        loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Np = loads["Np"]
        Tp = loads["Tp"]

        dNp_dprecurveTip_fd = np.zeros((self.n, 1))
        dTp_dprecurveTip_fd = np.zeros((self.n, 1))

        pct = float(precurveTip)
        delta = 1e-6 * pct
        pct += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
            precurve=rotor.precurve,
            precurveTip=pct,
        )

        loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]
        dNp_dprecurveTip_fd[:, 0] = (Npd - Np) / delta
        dTp_dprecurveTip_fd[:, 0] = (Tpd - Tp) / delta

        np.testing.assert_allclose(dNp_dprecurveTip_fd, 0.0, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dTp_dprecurveTip_fd, 0.0, rtol=1e-4, atol=1e-8)

    def test_dprecurveTip2(self):

        precurve = np.linspace(1, 10, self.n)
        precurveTip = precurve[-1]
        precone = 0.0
        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=True,
            precurve=precurve,
            precurveTip=precurveTip,
        )

        outputs, derivs = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
        P = outputs["P"]
        T = outputs["T"]
        Q = outputs["Q"]
        M = outputs["M"]
        dP = derivs["dP"]
        dT = derivs["dT"]
        dQ = derivs["dQ"]
        dM = derivs["dM"]

        dT_dprecurveTip = dT["dprecurveTip"]
        dQ_dprecurveTip = dQ["dprecurveTip"]
        dM_dprecurveTip = dM["dprecurveTip"]
        dP_dprecurveTip = dP["dprecurveTip"]

        dT_dprecurveTip_fd = np.zeros((self.npts, 1))
        dQ_dprecurveTip_fd = np.zeros((self.npts, 1))
        dM_dprecurveTip_fd = np.zeros((self.npts, 1))
        dP_dprecurveTip_fd = np.zeros((self.npts, 1))

        pct = float(precurveTip)
        delta = 1e-6 * pct
        pct += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
            precurve=rotor.precurve,
            precurveTip=pct,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
        Pd = outputs["P"]
        Td = outputs["T"]
        Qd = outputs["Q"]
        Md = outputs["M"]

        dT_dprecurveTip_fd[:, 0] = (Td - T) / delta
        dQ_dprecurveTip_fd[:, 0] = (Qd - Q) / delta
        dM_dprecurveTip_fd[:, 0] = (Md - M) / delta
        dP_dprecurveTip_fd[:, 0] = (Pd - P) / delta
        np.testing.assert_allclose(dT_dprecurveTip_fd, dT_dprecurveTip, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dQ_dprecurveTip_fd, dQ_dprecurveTip, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dM_dprecurveTip_fd, dM_dprecurveTip, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dP_dprecurveTip_fd, dP_dprecurveTip, rtol=1e-4, atol=1e-8)

    def test_dprecurveTip3(self):

        precurve = np.linspace(1, 10, self.n)
        precurveTip = precurve[-1]
        precone = 0.0
        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=True,
            precurve=precurve,
            precurveTip=precurveTip,
        )

        outputs, derivs = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
        CP = outputs["CP"]
        CT = outputs["CT"]
        CQ = outputs["CQ"]
        CM = outputs["CM"]
        dCP = derivs["dCP"]
        dCT = derivs["dCT"]
        dCQ = derivs["dCQ"]
        dCM = derivs["dCM"]

        dCT_dprecurveTip = dCT["dprecurveTip"]
        dCQ_dprecurveTip = dCQ["dprecurveTip"]
        dCM_dprecurveTip = dCM["dprecurveTip"]
        dCP_dprecurveTip = dCP["dprecurveTip"]

        dCT_dprecurveTip_fd = np.zeros((self.npts, 1))
        dCQ_dprecurveTip_fd = np.zeros((self.npts, 1))
        dCM_dprecurveTip_fd = np.zeros((self.npts, 1))
        dCP_dprecurveTip_fd = np.zeros((self.npts, 1))

        pct = float(precurveTip)
        delta = 1e-6 * pct
        pct += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
            precurve=rotor.precurve,
            precurveTip=pct,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
        CPd = outputs["CP"]
        CTd = outputs["CT"]
        CQd = outputs["CQ"]
        CMd = outputs["CM"]

        dCT_dprecurveTip_fd[:, 0] = (CTd - CT) / delta
        dCQ_dprecurveTip_fd[:, 0] = (CQd - CQ) / delta
        dCM_dprecurveTip_fd[:, 0] = (CMd - CM) / delta
        dCP_dprecurveTip_fd[:, 0] = (CPd - CP) / delta

        np.testing.assert_allclose(dCT_dprecurveTip_fd, dCT_dprecurveTip, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dCQ_dprecurveTip_fd, dCQ_dprecurveTip, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dCM_dprecurveTip_fd, dCM_dprecurveTip, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dCP_dprecurveTip_fd, dCP_dprecurveTip, rtol=1e-4, atol=1e-8)

    def test_dpresweepTip1(self):

        presweep = np.linspace(1, 10, self.n)
        presweepTip = presweep[-1]
        precone = 0.0
        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=True,
            presweep=presweep,
            presweepTip=presweepTip,
        )

        loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Np = loads["Np"]
        Tp = loads["Tp"]

        dNp_dpresweepTip_fd = np.zeros((self.n, 1))
        dTp_dpresweepTip_fd = np.zeros((self.n, 1))

        pst = float(presweepTip)
        delta = 1e-6 * pst
        pst += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
            presweep=rotor.presweep,
            presweepTip=pst,
        )

        loads, _ = rotor.distributedAeroLoads(self.Uinf, self.Omega, self.pitch, self.azimuth)
        Npd = loads["Np"]
        Tpd = loads["Tp"]
        dNp_dpresweepTip_fd[:, 0] = (Npd - Np) / delta
        dTp_dpresweepTip_fd[:, 0] = (Tpd - Tp) / delta

        np.testing.assert_allclose(dNp_dpresweepTip_fd, 0.0, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dTp_dpresweepTip_fd, 0.0, rtol=1e-4, atol=1e-8)

    def test_dpresweepTip2(self):

        presweep = np.linspace(1, 10, self.n)
        presweepTip = presweep[-1]
        precone = 0.0
        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=True,
            presweep=presweep,
            presweepTip=presweepTip,
        )

        outputs, derivs = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
        P = outputs["P"]
        T = outputs["T"]
        Q = outputs["Q"]
        M = outputs["M"]
        dP = derivs["dP"]
        dT = derivs["dT"]
        dQ = derivs["dQ"]
        dM = derivs["dM"]

        dT_dpresweepTip = dT["dpresweepTip"]
        dQ_dpresweepTip = dQ["dpresweepTip"]
        dM_dpresweepTip = dM["dpresweepTip"]
        dP_dpresweepTip = dP["dpresweepTip"]

        dT_dpresweepTip_fd = np.zeros((self.npts, 1))
        dQ_dpresweepTip_fd = np.zeros((self.npts, 1))
        dM_dpresweepTip_fd = np.zeros((self.npts, 1))
        dP_dpresweepTip_fd = np.zeros((self.npts, 1))

        pst = float(presweepTip)
        delta = 1e-6 * pst
        pst += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
            presweep=rotor.presweep,
            presweepTip=pst,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=False)
        Pd = outputs["P"]
        Td = outputs["T"]
        Qd = outputs["Q"]
        Md = outputs["M"]

        dT_dpresweepTip_fd[:, 0] = (Td - T) / delta
        dQ_dpresweepTip_fd[:, 0] = (Qd - Q) / delta
        dM_dpresweepTip_fd[:, 0] = (Md - M) / delta
        dP_dpresweepTip_fd[:, 0] = (Pd - P) / delta

        np.testing.assert_allclose(dT_dpresweepTip_fd, dT_dpresweepTip, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dQ_dpresweepTip_fd, dQ_dpresweepTip, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dM_dpresweepTip_fd, dM_dpresweepTip, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dP_dpresweepTip_fd, dP_dpresweepTip, rtol=1e-4, atol=1e-8)

    def test_dpresweepTip3(self):

        presweep = np.linspace(1, 10, self.n)
        presweepTip = presweep[-1]
        precone = 0.0
        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=True,
            presweep=presweep,
            presweepTip=presweepTip,
        )

        outputs, derivs = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
        CP = outputs["CP"]
        CT = outputs["CT"]
        CQ = outputs["CQ"]
        CM = outputs["CM"]
        dCP = derivs["dCP"]
        dCT = derivs["dCT"]
        dCQ = derivs["dCQ"]
        dCM = derivs["dCM"]

        dCT_dpresweepTip = dCT["dpresweepTip"]
        dCQ_dpresweepTip = dCQ["dpresweepTip"]
        dCM_dpresweepTip = dCM["dpresweepTip"]
        dCP_dpresweepTip = dCP["dpresweepTip"]

        dCT_dpresweepTip_fd = np.zeros((self.npts, 1))
        dCQ_dpresweepTip_fd = np.zeros((self.npts, 1))
        dCM_dpresweepTip_fd = np.zeros((self.npts, 1))
        dCP_dpresweepTip_fd = np.zeros((self.npts, 1))

        pst = float(presweepTip)
        delta = 1e-6 * pst
        pst += delta

        rotor = CCBlade(
            self.r,
            self.chord,
            self.theta,
            self.af,
            self.Rhub,
            self.Rtip,
            self.B,
            self.rho,
            self.mu,
            precone,
            self.tilt,
            self.yaw,
            self.shearExp,
            self.hubHt,
            self.nSector,
            derivatives=False,
            presweep=rotor.presweep,
            presweepTip=pst,
        )

        outputs, _ = rotor.evaluate([self.Uinf], [self.Omega], [self.pitch], coefficients=True)
        CPd = outputs["CP"]
        CTd = outputs["CT"]
        CQd = outputs["CQ"]
        CMd = outputs["CM"]

        dCT_dpresweepTip_fd[:, 0] = (CTd - CT) / delta
        dCQ_dpresweepTip_fd[:, 0] = (CQd - CQ) / delta
        dCM_dpresweepTip_fd[:, 0] = (CMd - CM) / delta
        dCP_dpresweepTip_fd[:, 0] = (CPd - CP) / delta

        np.testing.assert_allclose(dCT_dpresweepTip_fd, dCT_dpresweepTip, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dCQ_dpresweepTip_fd, dCQ_dpresweepTip, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dCM_dpresweepTip_fd, dCM_dpresweepTip, rtol=1e-4, atol=1e-8)
        np.testing.assert_allclose(dCP_dpresweepTip_fd, dCP_dpresweepTip, rtol=1e-4, atol=1e-8)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestGradients))
    suite.addTest(unittest.makeSuite(TestGradientsNotRotating))
    suite.addTest(unittest.makeSuite(TestGradientsFreestreamArray))
    suite.addTest(unittest.makeSuite(TestGradients_RHub_Tip))
    return suite


if __name__ == "__main__":
    unittest.TextTestRunner().run(suite())
