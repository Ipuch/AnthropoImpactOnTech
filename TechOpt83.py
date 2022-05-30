"""
The goal of this program is to optimize de movement to acheive a rudi out pike (803<).
"""
import numpy as np
import biorbd_casadi as biorbd
from casadi import MX, Function
from bioptim import (
    OptimalControlProgram,
    DynamicsList,
    DynamicsFcn,
    ObjectiveList,
    ObjectiveFcn,
    BoundsList,
    QAndQDotBounds,
    InitialGuessList,
    InterpolationType,
    OdeSolver,
    Node,
    Solver,
    BiMappingList,
    CostType,
    ConstraintList,
    ConstraintFcn,
    PenaltyNodeList,
    BiorbdInterface,
)
import time


def minimize_dofs(all_pn: PenaltyNodeList, dofs: list, targets: list) -> MX:
    diff = 0
    for i, dof in enumerate(dofs):
        diff += (all_pn.nlp.states['q'].mx[dof] - targets[i])**2
    return BiorbdInterface.mx_to_cx('minimize_dofs', diff, all_pn.nlp.states['q'])

def prepare_ocp(
    biorbd_model_path: str, n_shooting: int, final_time: float, ode_solver: OdeSolver = OdeSolver.RK4()
) -> OptimalControlProgram:
    """
    Prepare the ocp

    Parameters
    ----------
    biorbd_model_path: str
        The path to the bioMod file
    n_shooting: int
        The number of shooting points
    final_time: float
        The time at the final node
    ode_solver: OdeSolver
        The ode solver to use

    Returns
    -------
    The OptimalControlProgram ready to be solved
    """

    biorbd_model = ( biorbd.Model(biorbd_model_path), biorbd.Model(biorbd_model_path), biorbd.Model(biorbd_model_path), biorbd.Model(biorbd_model_path), biorbd.Model(biorbd_model_path) )

    nb_q = biorbd_model[0].nbQ()
    nb_qdot = biorbd_model[0].nbQdot()
    n_tau = nb_q - biorbd_model[0].nbRoot()

    # Pour la lisibilite
    X = 0
    Y = 1
    Z = 2
    Xrot = 3
    Yrot = 4
    Zrot = 5
    ZrotBD = 6
    YrotBD = 7
    ZrotABD = 8
    YrotABD = 9
    ZrotBG = 10
    YrotBG = 11
    ZrotABG = 12
    YrotABG = 13
    XrotC = 14
    YrotC = 15
    vX = 0 + nb_q
    vY = 1 + nb_q
    vZ = 2 + nb_q
    vXrot = 3 + nb_q
    vYrot = 4 + nb_q
    vZrot = 5 + nb_q
    vZrotBD = 6 + nb_q
    vYrotBD = 7 + nb_q
    vZrotABD = 8 + nb_q
    vYrotABD = 9 + nb_q
    vZrotBG = 10 + nb_q
    vYrotBG = 11 + nb_q
    vZrotABG = 12 + nb_q
    vYrotABG = 13 + nb_q
    vXrotC = 14 + nb_q
    vYrotC = 15 + nb_q

    # Add objective functions
    objective_functions = ObjectiveList()
    # objective_functions.add(ObjectiveFcn.Mayer.MINIMIZE_MARKERS, marker_index=1, weight=-1)
    objective_functions.add(ObjectiveFcn.Lagrange.MINIMIZE_CONTROL, key="tau", node=Node.ALL_SHOOTING, weight=1, phase=0)
    objective_functions.add(ObjectiveFcn.Lagrange.MINIMIZE_CONTROL, key="tau", node=Node.ALL_SHOOTING, weight=1, phase=1)
    objective_functions.add(ObjectiveFcn.Lagrange.MINIMIZE_CONTROL, key="tau", node=Node.ALL_SHOOTING, weight=1, phase=2)
    objective_functions.add(ObjectiveFcn.Lagrange.MINIMIZE_CONTROL, key="tau", node=Node.ALL_SHOOTING, weight=1, phase=3)
    objective_functions.add(ObjectiveFcn.Lagrange.MINIMIZE_CONTROL, key="tau", node=Node.ALL_SHOOTING, weight=1, phase=4)

    objective_functions.add(ObjectiveFcn.Mayer.MINIMIZE_TIME, min_bound=.0, max_bound=final_time, weight=100000, phase=0)
    # objective_functions.add(ObjectiveFcn.Mayer.MINIMIZE_TIME, min_bound=.0, max_bound=final_time, weight=.01, phase=1)
    # objective_functions.add(ObjectiveFcn.Mayer.MINIMIZE_TIME, min_bound=.0, max_bound=final_time, weight=.01, phase=2)
    # objective_functions.add(ObjectiveFcn.Mayer.MINIMIZE_TIME, min_bound=.0, max_bound=final_time, weight=.01, phase=3)
    # objective_functions.add(ObjectiveFcn.Mayer.MINIMIZE_TIME, min_bound=.0, max_bound=final_time, weight=.01, phase=4)

    objective_functions.add(ObjectiveFcn.Mayer.SUPERIMPOSE_MARKERS, node=Node.END, first_marker='MidMainG', second_marker='CibleMainG', weight=1000, phase=0)
    objective_functions.add(ObjectiveFcn.Mayer.SUPERIMPOSE_MARKERS, node=Node.END, first_marker='MidMainD', second_marker='CibleMainD', weight=1000, phase=0)

    # arrete de gigoter les bras
    les_bras = [ZrotBD, YrotBD, ZrotABD, YrotABD, ZrotBG, YrotBG, ZrotABG, YrotABG]
    objective_functions.add(minimize_dofs, custom_type=ObjectiveFcn.Lagrange, dofs=les_bras, targets=np.zeros(len(les_bras)), weight=100, phase=2)
    objective_functions.add(minimize_dofs, custom_type=ObjectiveFcn.Lagrange, dofs=les_bras, targets=np.zeros(len(les_bras)), weight=100, phase=3)

    # Dynamics
    dynamics = DynamicsList()
    dynamics.add(DynamicsFcn.TORQUE_DRIVEN)
    dynamics.add(DynamicsFcn.TORQUE_DRIVEN)
    dynamics.add(DynamicsFcn.TORQUE_DRIVEN)
    dynamics.add(DynamicsFcn.TORQUE_DRIVEN)
    dynamics.add(DynamicsFcn.TORQUE_DRIVEN)

    # Define control path constraint  TODO: generaliser les mapping avec for peut-etre
    dof_mappings = BiMappingList()
    dof_mappings.add("tau", to_second=[None, None, None, None, None, None, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9], to_first=[6, 7, 8, 9, 10, 11, 12, 13, 14, 15], phase=0)
    dof_mappings.add("tau", to_second=[None, None, None, None, None, None, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9], to_first=[6, 7, 8, 9, 10, 11, 12, 13, 14, 15], phase=1)
    dof_mappings.add("tau", to_second=[None, None, None, None, None, None, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9], to_first=[6, 7, 8, 9, 10, 11, 12, 13, 14, 15], phase=2)
    dof_mappings.add("tau", to_second=[None, None, None, None, None, None, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9], to_first=[6, 7, 8, 9, 10, 11, 12, 13, 14, 15], phase=3)
    dof_mappings.add("tau", to_second=[None, None, None, None, None, None, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9], to_first=[6, 7, 8, 9, 10, 11, 12, 13, 14, 15], phase=4)

    tau_min, tau_max, tau_init = -500, 500, 0
    u_bounds = BoundsList()
    u_bounds.add([tau_min] * n_tau, [tau_max] * n_tau)
    u_bounds.add([tau_min] * n_tau, [tau_max] * n_tau)
    u_bounds.add([tau_min] * n_tau, [tau_max] * n_tau)
    u_bounds.add([tau_min] * n_tau, [tau_max] * n_tau)
    u_bounds.add([tau_min] * n_tau, [tau_max] * n_tau)

    u_init = InitialGuessList()
    u_init.add([tau_init] * n_tau)
    u_init.add([tau_init] * n_tau)
    u_init.add([tau_init] * n_tau)
    u_init.add([tau_init] * n_tau)
    u_init.add([tau_init] * n_tau)

    # Path constraint
    x_bounds = BoundsList()
    x_bounds.add(bounds=QAndQDotBounds(biorbd_model[0]))
    x_bounds.add(bounds=QAndQDotBounds(biorbd_model[0]))
    x_bounds.add(bounds=QAndQDotBounds(biorbd_model[0]))
    x_bounds.add(bounds=QAndQDotBounds(biorbd_model[0]))
    x_bounds.add(bounds=QAndQDotBounds(biorbd_model[0]))

    # Pour la lisibilite
    DEBUT, MILIEU, FIN = 0, 1, 2

    #
    # Contraintes de position: PHASE 0 la montee en carpe
    #

    # deplacement
    x_bounds[0].min[X, :] = -.1
    x_bounds[0].max[X, :] = .1
    x_bounds[0].min[Y, :] = -1.
    x_bounds[0].max[Y, :] = 1.
    x_bounds[0].min[:Z+1, DEBUT] = 0
    x_bounds[0].max[:Z+1, DEBUT] = 0
    x_bounds[0].min[Z, MILIEU:] = 0
    x_bounds[0].max[Z, MILIEU:] = 20  # beaucoup plus que necessaire, juste pour que la parabole fonctionne

    # le salto autour de x
    x_bounds[0].min[Xrot, DEBUT] = -.50  # penche vers l'avant un peu carpe
    x_bounds[0].max[Xrot, DEBUT] = -.35
    x_bounds[0].min[Xrot, MILIEU:] = -4 * 3.14 - .1  # salto
    x_bounds[0].max[Xrot, MILIEU:] = 0
    # limitation du tilt autour de y
    x_bounds[0].min[Yrot, DEBUT] = 0
    x_bounds[0].max[Yrot, DEBUT] = 0
    x_bounds[0].min[Yrot, MILIEU:] = - 3.14 / 16  # vraiment pas suppose tilte
    x_bounds[0].max[Yrot, MILIEU:] = 3.14 / 16
    # la vrille autour de z
    x_bounds[0].min[Zrot, DEBUT] = 0
    x_bounds[0].max[Zrot, DEBUT] = 0
    x_bounds[0].min[Zrot, MILIEU:] = -.1  # pas de vrille dans cette phase
    x_bounds[0].max[Zrot, MILIEU:] = .1

    # bras droit
    x_bounds[0].min[YrotBD, DEBUT] = -2.9  # debut bras aux oreilles
    x_bounds[0].max[YrotBD, DEBUT] = -2.9
    x_bounds[0].min[ZrotBD, DEBUT] = 0
    x_bounds[0].max[ZrotBD, DEBUT] = 0
    # bras gauche
    x_bounds[0].min[YrotBG, DEBUT] = 2.9  # debut bras aux oreilles
    x_bounds[0].max[YrotBG, DEBUT] = 2.9
    x_bounds[0].min[ZrotBG, DEBUT] = 0
    x_bounds[0].max[ZrotBG, DEBUT] = 0

    # coude droit
    x_bounds[0].min[ZrotABD:YrotABD+1, DEBUT] = 0
    x_bounds[0].max[ZrotABD:YrotABD+1, DEBUT] = 0
    # coude gauche
    x_bounds[0].min[ZrotABG:YrotABG+1, DEBUT] = 0
    x_bounds[0].max[ZrotABG:YrotABG+1, DEBUT] = 0

    # le carpe
    x_bounds[0].min[XrotC, DEBUT] = .35  # depart un peu ferme aux hanches
    x_bounds[0].max[XrotC, DEBUT] = .50
    x_bounds[0].min[XrotC, FIN] = 2.5
    # x_bounds[0].max[XrotC, FIN] = 2.7  # max du modele
    # le dehanchement
    x_bounds[0].min[YrotC, DEBUT] = 0
    x_bounds[0].max[YrotC, DEBUT] = 0
    x_bounds[0].min[YrotC, MILIEU:] = -.1
    x_bounds[0].max[YrotC, MILIEU:] = .1

    # Contraintes de vitesse: PHASE 0 la montee en carpe

    vzinit = 9.81 / 2 * final_time  # vitesse initiale en z du CoM pour revenir a terre au temps final

    # decalage entre le bassin et le CoM
    CoM_Q_sym = MX.sym('CoM', nb_q)
    CoM_Q_init = np.zeros(nb_q)
    CoM_Q_func = Function('CoM_Q_func', [CoM_Q_sym], [biorbd_model[0].CoM(CoM_Q_sym).to_mx()])
    bassin_Q_func = Function('bassin_Q_func', [CoM_Q_sym],
                             [biorbd_model[0].globalJCS(0).to_mx()])  # retourne la RT du bassin

    v = np.array(CoM_Q_func(CoM_Q_init)).reshape(1, 3) - np.array(bassin_Q_func(CoM_Q_init))[-1, :3]  # selectionne seulement la translation

    # en xy bassin
    x_bounds[0].min[vX:vY+1, :] = -10
    x_bounds[0].max[vX:vY+1, :] = 10
    x_bounds[0].min[vX:vY+1, DEBUT] = -.5
    x_bounds[0].max[vX:vY+1, DEBUT] = .5
    # z bassin
    x_bounds[0].min[vZ, :] = -100
    x_bounds[0].max[vZ, :] = 100
    x_bounds[0].min[vZ, DEBUT] = vzinit - .1
    x_bounds[0].max[vZ, DEBUT] = vzinit + .1

    # autour de x
    x_bounds[0].min[vXrot, :] = -100
    x_bounds[0].max[vXrot, :] = 100
    x_bounds[0].min[vXrot, DEBUT] = 0  # pas de contre rotation au debut, juste pour etre certain
    # autour de y
    x_bounds[0].min[vYrot, :] = -100
    x_bounds[0].max[vYrot, :] = 100
    x_bounds[0].min[vYrot, DEBUT] = 0
    x_bounds[0].max[vYrot, DEBUT] = 0
    # autour de z
    x_bounds[0].min[vZrot, :] = -100
    x_bounds[0].max[vZrot, :] = 100
    x_bounds[0].min[vZrot, DEBUT] = 0
    x_bounds[0].max[vZrot, DEBUT] = 0

    # tenir compte du decalage entre bassin et CoM avec la rotation
    # Qtransdot = Qtransdot + v cross Qrotdot
    x_bounds[0].min[vX:vZ+1, DEBUT] = x_bounds[0].min[vX:vZ+1, DEBUT] + np.cross(v, x_bounds[0].min[vXrot:vZrot+1, DEBUT])
    x_bounds[0].max[vX:vZ+1, DEBUT] = x_bounds[0].max[vX:vZ+1, DEBUT] + np.cross(v, x_bounds[0].max[vXrot:vZrot+1, DEBUT])

    # bras droit
    x_bounds[0].min[vZrotBD:vYrotBD+1, :] = -100
    x_bounds[0].max[vZrotBD:vYrotBD+1, :] = 100
    x_bounds[0].min[vZrotBD:vYrotBD+1, DEBUT] = 0
    x_bounds[0].max[vZrotBD:vYrotBD+1, DEBUT] = 0
    # bras droit
    x_bounds[0].min[vZrotBG:vYrotBG+1, :] = -100
    x_bounds[0].max[vZrotBG:vYrotBG+1, :] = 100
    x_bounds[0].min[vZrotBG:vYrotBG+1, DEBUT] = 0
    x_bounds[0].max[vZrotBG:vYrotBG+1, DEBUT] = 0

    # coude droit
    x_bounds[0].min[vZrotABD:vYrotABD+1, :] = -100
    x_bounds[0].max[vZrotABD:vYrotABD+1, :] = 100
    x_bounds[0].min[vZrotABD:vYrotABD+1, DEBUT] = 0
    x_bounds[0].max[vZrotABD:vYrotABD+1, DEBUT] = 0
    # coude gauche
    x_bounds[0].min[vZrotABD:vYrotABG+1, :] = -100
    x_bounds[0].max[vZrotABD:vYrotABG+1, :] = 100
    x_bounds[0].min[vZrotABG:vYrotABG+1, DEBUT] = 0
    x_bounds[0].max[vZrotABG:vYrotABG+1, DEBUT] = 0

    # du carpe
    x_bounds[0].min[vXrotC, :] = -100
    x_bounds[0].max[vXrotC, :] = 100
    x_bounds[0].min[vXrotC, DEBUT] = 0
    x_bounds[0].max[vXrotC, DEBUT] = 0
    # du dehanchement
    x_bounds[0].min[vYrotC, :] = -100
    x_bounds[0].max[vYrotC, :] = 100
    x_bounds[0].min[vYrotC, DEBUT] = 0
    x_bounds[0].max[vYrotC, DEBUT] = 0

    #
    # Contraintes de position: PHASE 1 le salto carpe
    #

    # deplacement
    x_bounds[1].min[X, :] = -.1
    x_bounds[1].max[X, :] = .1
    x_bounds[1].min[Y, :] = -1.
    x_bounds[1].max[Y, :] = 1.
    x_bounds[1].min[Z, :] = 0
    x_bounds[1].max[Z, :] = 20  # beaucoup plus que necessaire, juste pour que la parabole fonctionne

    # le salto autour de x
    x_bounds[1].min[Xrot, :] = -4 * 3.14
    x_bounds[1].max[Xrot, :] = 0
    x_bounds[1].max[Xrot, FIN] = -2 * 3.14 + .1
    # limitation du tilt autour de y
    x_bounds[1].min[Yrot, :] = - 3.14 / 16
    x_bounds[1].max[Yrot, :] = 3.14 / 16
    # la vrille autour de z
    x_bounds[1].min[Zrot, :] = -.1
    x_bounds[1].max[Zrot, :] = .1

    # bras droit  f4a a l'ouverture
    # x_bounds[1].min[YrotD, DEBUT] = -2.9  # debut bras aux oreilles
    # x_bounds[1].max[YrotD, DEBUT] = -2.9
    # x_bounds[1].min[ZrotD, DEBUT] = 0
    # x_bounds[1].max[ZrotD, DEBUT] = 0
    # bras gauche
    # x_bounds[1].min[YrotG, DEBUT] = 2.9  # debut bras aux oreilles
    # x_bounds[1].max[YrotG, DEBUT] = 2.9
    # x_bounds[1].min[ZrotG, DEBUT] = 0
    # x_bounds[1].max[ZrotG, DEBUT] = 0

    # le carpe
    x_bounds[1].min[XrotC, :] = 2.5
    # x_bounds[1].max[XrotC, :] = 2.7  # contraint par le model
    # le dehanchement
    x_bounds[1].min[YrotC, DEBUT] = -.1
    x_bounds[1].max[YrotC, DEBUT] = .1


    # Contraintes de vitesse: PHASE 1 le salto carpe

    # en xy bassin
    x_bounds[1].min[vX:vY + 1, :] = -10
    x_bounds[1].max[vX:vY + 1, :] = 10

    # z bassin
    x_bounds[1].min[vZ, :] = -100
    x_bounds[1].max[vZ, :] = 100

    # autour de x
    x_bounds[1].min[vXrot, :] = -100
    x_bounds[1].max[vXrot, :] = 100
    # autour de y
    x_bounds[1].min[vYrot, :] = -100
    x_bounds[1].max[vYrot, :] = 100

    # autour de z
    x_bounds[1].min[vZrot, :] = -100
    x_bounds[1].max[vZrot, :] = 100

    # bras droit
    x_bounds[1].min[vZrotBD:vYrotBD + 1, :] = -100
    x_bounds[1].max[vZrotBD:vYrotBD + 1, :] = 100
    # bras droit
    x_bounds[1].min[vZrotBG:vYrotBG + 1, :] = -100
    x_bounds[1].max[vZrotBG:vYrotBG + 1, :] = 100

    # coude droit
    x_bounds[1].min[vZrotABD:vYrotABD + 1, :] = -100
    x_bounds[1].max[vZrotABD:vYrotABD + 1, :] = 100
    # coude gauche
    x_bounds[1].min[vZrotABD:vYrotABG + 1, :] = -100
    x_bounds[1].max[vZrotABD:vYrotABG + 1, :] = 100

    # du carpe
    x_bounds[1].min[vXrotC, :] = -100
    x_bounds[1].max[vXrotC, :] = 100
    # du dehanchement
    x_bounds[1].min[vYrotC, :] = -100
    x_bounds[1].max[vYrotC, :] = 100

    #
    # Contraintes de position: PHASE 2 l'ouverture
    #

    # deplacement
    x_bounds[2].min[X, :] = -.2
    x_bounds[2].max[X, :] = .2
    x_bounds[2].min[Y, :] = -1.
    x_bounds[2].max[Y, :] = 1.
    x_bounds[2].min[Z, :] = 0
    x_bounds[2].max[Z, :] = 20  # beaucoup plus que necessaire, juste pour que la parabole fonctionne

    # le salto autour de x
    x_bounds[2].min[Xrot, :] = -4 * 3.14
    x_bounds[2].max[Xrot, :] = -2 * 3.14 - .1  # 1 salto 3/4
    # limitation du tilt autour de y
    x_bounds[2].min[Yrot, :] = - 3.14 / 4
    x_bounds[2].max[Yrot, :] = 3.14 / 4
    # la vrille autour de z
    x_bounds[2].min[Zrot, :] = 0
    x_bounds[2].max[Zrot, :] = 3 * 3.14

    # bras droit  f4a a l'ouverture
    # x_bounds[2].min[YrotD, DEBUT] = -2.9  # debut bras aux oreilles
    # x_bounds[2].max[YrotD, DEBUT] = -2.9
    # x_bounds[2].min[ZrotD, DEBUT] = 0
    # x_bounds[2].max[ZrotD, DEBUT] = 0
    # bras gauche
    # x_bounds[2].min[YrotG, DEBUT] = 2.9  # debut bras aux oreilles
    # x_bounds[2].max[YrotG, DEBUT] = 2.9
    # x_bounds[2].min[ZrotG, DEBUT] = 0
    # x_bounds[2].max[ZrotG, DEBUT] = 0

    # le carpe
    # x_bounds[2].min[XrotC, DEBUT] = 0
    # x_bounds[2].max[XrotC, DEBUT] = 0
    # x_bounds[2].min[XrotC, FIN] = 2.8  # min du modele
    x_bounds[2].max[XrotC, FIN] = .7
    # le dehanchement
    # x_bounds[2].min[YrotC, DEBUT] = -.05
    # x_bounds[2].max[YrotC, DEBUT] = .05
    # x_bounds[2].min[YrotC, MILIEU:] = -.05  # f4a a l'ouverture
    # x_bounds[2].max[YrotC, MILIEU:] = .05

    # Contraintes de vitesse: PHASE 2 l'ouverture

    # en xy bassin
    x_bounds[2].min[vX:vY + 1, :] = -10
    x_bounds[2].max[vX:vY + 1, :] = 10

    # z bassin
    x_bounds[2].min[vZ, :] = -100
    x_bounds[2].max[vZ, :] = 100

    # autour de x
    x_bounds[2].min[vXrot, :] = -100
    x_bounds[2].max[vXrot, :] = 100
    # autour de y
    x_bounds[2].min[vYrot, :] = -100
    x_bounds[2].max[vYrot, :] = 100

    # autour de z
    x_bounds[2].min[vZrot, :] = -100
    x_bounds[2].max[vZrot, :] = 100

    # bras droit
    x_bounds[2].min[vZrotBD:vYrotBD + 1, :] = -100
    x_bounds[2].max[vZrotBD:vYrotBD + 1, :] = 100
    # bras droit
    x_bounds[2].min[vZrotBG:vYrotBG + 1, :] = -100
    x_bounds[2].max[vZrotBG:vYrotBG + 1, :] = 100

    # coude droit
    x_bounds[2].min[vZrotABD:vYrotABD + 1, :] = -100
    x_bounds[2].max[vZrotABD:vYrotABD + 1, :] = 100
    # coude gauche
    x_bounds[2].min[vZrotABD:vYrotABG + 1, :] = -100
    x_bounds[2].max[vZrotABD:vYrotABG + 1, :] = 100

    # du carpe
    x_bounds[2].min[vXrotC, :] = -100
    x_bounds[2].max[vXrotC, :] = 100
    # du dehanchement
    x_bounds[2].min[vYrotC, :] = -100
    x_bounds[2].max[vYrotC, :] = 100

    #
    # Contraintes de position: PHASE 3 la vrille et demie
    #

    # deplacement
    x_bounds[3].min[X, :] = -.2
    x_bounds[3].max[X, :] = .2
    x_bounds[3].min[Y, :] = -1.
    x_bounds[3].max[Y, :] = 1.
    x_bounds[3].min[Z, :] = 0
    x_bounds[3].max[Z, :] = 20  # beaucoup plus que necessaire, juste pour que la parabole fonctionne

    # le salto autour de x
    x_bounds[3].min[Xrot, :] = -2 * 3.14 - 3/2 * 3.14 - .1  # 1 salto 3/4
    x_bounds[3].max[Xrot, :] = -2 * 3.14 + .1
    x_bounds[3].min[Xrot, FIN] = -2 * 3.14 - 3/2 * 3.14 - .1  # 1 salto 3/4
    x_bounds[3].max[Xrot, FIN] = -2 * 3.14 - 3/2 * 3.14 + .1
    # limitation du tilt autour de y
    x_bounds[3].min[Yrot, :] = - 3.14 / 4
    x_bounds[3].max[Yrot, :] = 3.14 / 4
    x_bounds[3].min[Yrot, FIN] = - 3.14 / 8
    x_bounds[3].max[Yrot, FIN] = 3.14 / 8
    # la vrille autour de z
    x_bounds[3].min[Zrot, :] = 0
    x_bounds[3].max[Zrot, :] = 3 * 3.14
    x_bounds[3].min[Zrot, FIN] = 3 * 3.14 - .1  # complete la vrille
    x_bounds[3].max[Zrot, FIN] = 3 * 3.14 + .1

    # bras droit  f4a la vrille
    # x_bounds[3].min[YrotD, DEBUT] = -2.9  # debut bras aux oreilles
    # x_bounds[3].max[YrotD, DEBUT] = -2.9
    # x_bounds[3].min[ZrotD, DEBUT] = 0
    # x_bounds[3].max[ZrotD, DEBUT] = 0
    # bras gauche
    # x_bounds[3].min[YrotG, DEBUT] = 2.9  # debut bras aux oreilles
    # x_bounds[3].max[YrotG, DEBUT] = 2.9
    # x_bounds[3].min[ZrotG, DEBUT] = 0
    # x_bounds[3].max[ZrotG, DEBUT] = 0

    # le carpe  f4a les jambes
    # x_bounds[3].min[XrotC, :] = 2.8  # min du modele
    x_bounds[3].max[XrotC, :] = .7
    # le dehanchement
    # x_bounds[3].min[YrotC, DEBUT] = -.05
    # x_bounds[3].max[YrotC, DEBUT] = .05
    # x_bounds[3].min[YrotC, MILIEU:] = -.05  # f4a a l'ouverture
    # x_bounds[3].max[YrotC, MILIEU:] = .05

    # Contraintes de vitesse: PHASE 3 la vrille et demie

    # en xy bassin
    x_bounds[3].min[vX:vY + 1, :] = -10
    x_bounds[3].max[vX:vY + 1, :] = 10

    # z bassin
    x_bounds[3].min[vZ, :] = -100
    x_bounds[3].max[vZ, :] = 100

    # autour de x
    x_bounds[3].min[vXrot, :] = -100
    x_bounds[3].max[vXrot, :] = 100
    # autour de y
    x_bounds[3].min[vYrot, :] = -100
    x_bounds[3].max[vYrot, :] = 100

    # autour de z
    x_bounds[3].min[vZrot, :] = -100
    x_bounds[3].max[vZrot, :] = 100

    # bras droit
    x_bounds[3].min[vZrotBD:vYrotBD + 1, :] = -100
    x_bounds[3].max[vZrotBD:vYrotBD + 1, :] = 100
    # bras droit
    x_bounds[3].min[vZrotBG:vYrotBG + 1, :] = -100
    x_bounds[3].max[vZrotBG:vYrotBG + 1, :] = 100

    # coude droit
    x_bounds[3].min[vZrotABD:vYrotABD + 1, :] = -100
    x_bounds[3].max[vZrotABD:vYrotABD + 1, :] = 100
    # coude gauche
    x_bounds[3].min[vZrotABD:vYrotABG + 1, :] = -100
    x_bounds[3].max[vZrotABD:vYrotABG + 1, :] = 100

    # du carpe
    x_bounds[3].min[vXrotC, :] = -100
    x_bounds[3].max[vXrotC, :] = 100
    # du dehanchement
    x_bounds[3].min[vYrotC, :] = -100
    x_bounds[3].max[vYrotC, :] = 100

    #
    # Contraintes de position: PHASE 4 la reception
    #

    # deplacement
    x_bounds[4].min[:Y + 1, :] = -.1
    x_bounds[4].max[:Y + 1, :] = .1
    x_bounds[4].min[Z, :] = 0
    x_bounds[4].max[Z, :] = 20  # beaucoup plus que necessaire, juste pour que la parabole fonctionne
    x_bounds[4].min[Z, FIN] = 0
    x_bounds[4].max[Z, FIN] = .1

    # le salto autour de x
    x_bounds[4].min[Xrot, :] = -4 * 3.14
    x_bounds[4].max[Xrot, :] = -2 * 3.14 - 3 / 2 * 3.14 + .2  # 1 salto 3/4
    x_bounds[4].min[Xrot, FIN] = -4 * 3.14 - .1  # 1 salto 3/4
    x_bounds[4].max[Xrot, FIN] = -4 * 3.14 + .1
    # limitation du tilt autour de y
    x_bounds[4].min[Yrot, :] = - 3.14 / 16
    x_bounds[4].max[Yrot, :] = 3.14 / 16
    # la vrille autour de z
    x_bounds[4].min[Zrot, :] = 3 * 3.14 - .1  # complete la vrille
    x_bounds[4].max[Zrot, :] = 3 * 3.14 + .1

    # bras droit
    x_bounds[4].min[YrotBD, FIN] = -2.9 - .1  # debut bras aux oreilles
    x_bounds[4].max[YrotBD, FIN] = -2.9 + .1
    x_bounds[4].min[ZrotBD, FIN] = -.1
    x_bounds[4].max[ZrotBD, FIN] = .1
    # bras gauche
    x_bounds[4].min[YrotBG, FIN] = 2.9 - .1  # debut bras aux oreilles
    x_bounds[4].max[YrotBG, FIN] = 2.9 + .1
    x_bounds[4].min[ZrotBG, FIN] = -.1
    x_bounds[4].max[ZrotBG, FIN] = .1

    # coude droit
    x_bounds[4].min[ZrotABD:YrotABD + 1, FIN] = -.1
    x_bounds[4].max[ZrotABD:YrotABD + 1, FIN] = .1
    # coude gauche
    x_bounds[4].min[ZrotABG:YrotABG + 1, FIN] = -.1
    x_bounds[4].max[ZrotABG:YrotABG + 1, FIN] = .1

    # le carpe
    # x_bounds[4].min[XrotC, FIN] = 0  # min du modele
    x_bounds[4].max[XrotC, FIN] = .7
    # le dehanchement
    x_bounds[4].min[YrotC, FIN] = -.1
    x_bounds[4].max[YrotC, FIN] = .1

    # Contraintes de vitesse: PHASE 4 la reception

    # en xy bassin
    x_bounds[4].min[vX:vY + 1, :] = -10
    x_bounds[4].max[vX:vY + 1, :] = 10

    # z bassin
    x_bounds[4].min[vZ, :] = -100
    x_bounds[4].max[vZ, :] = 100

    # autour de x
    x_bounds[4].min[vXrot, :] = -100
    x_bounds[4].max[vXrot, :] = 100
    # autour de y
    x_bounds[4].min[vYrot, :] = -100
    x_bounds[4].max[vYrot, :] = 100

    # autour de z
    x_bounds[4].min[vZrot, :] = -100
    x_bounds[4].max[vZrot, :] = 100

    # bras droit
    x_bounds[4].min[vZrotBD:vYrotBD + 1, :] = -100
    x_bounds[4].max[vZrotBD:vYrotBD + 1, :] = 100
    # bras droit
    x_bounds[4].min[vZrotBG:vYrotBG + 1, :] = -100
    x_bounds[4].max[vZrotBG:vYrotBG + 1, :] = 100

    # coude droit
    x_bounds[4].min[vZrotABD:vYrotABD + 1, :] = -100
    x_bounds[4].max[vZrotABD:vYrotABD + 1, :] = 100
    # coude gauche
    x_bounds[4].min[vZrotABD:vYrotABG + 1, :] = -100
    x_bounds[4].max[vZrotABD:vYrotABG + 1, :] = 100

    # du carpe
    x_bounds[4].min[vXrotC, :] = -100
    x_bounds[4].max[vXrotC, :] = 100
    # du dehanchement
    x_bounds[4].min[vYrotC, :] = -100
    x_bounds[4].max[vYrotC, :] = 100

    #
    # Initial guesses
    #
    x0 = np.vstack((np.zeros((nb_q, 2)), np.zeros((nb_qdot, 2))))
    x1 = np.vstack((np.zeros((nb_q, 2)), np.zeros((nb_qdot, 2))))
    x2 = np.vstack((np.zeros((nb_q, 2)), np.zeros((nb_qdot, 2))))
    x3 = np.vstack((np.zeros((nb_q, 2)), np.zeros((nb_qdot, 2))))
    x4 = np.vstack((np.zeros((nb_q, 2)), np.zeros((nb_qdot, 2))))

    # x0[Xrot, 1] = -2 * 3.14
    x0[ZrotBG] = .75
    x0[ZrotBD] = -.75
    x0[YrotBG, 0] = 2.9
    x0[YrotBD, 0] = -2.9
    x0[YrotBG, 1] = 1.35
    x0[YrotBD, 1] = -1.35
    x0[XrotC, 0] = .4
    x0[XrotC, 1] = 2.65

    x1[ZrotBG] = .75
    x1[ZrotBD] = -.75
    x1[Xrot, 1] = -2 * 3.14
    x1[YrotBG] = 1.35
    x1[YrotBD] = -1.35
    x1[XrotC] = 2.6

    x2[Xrot] = -2 * 3.14
    x2[Zrot, 1] = 3.14
    x2[ZrotBG, 0] = .75
    x2[ZrotBD, 0] = -.75
    x2[YrotBG, 0] = 1.35
    x2[YrotBD, 0] = -1.35
    x2[XrotC, 0] = 2.6

    x3[Xrot, 0] = -2 * 3.14
    x3[Xrot, 1] = -2 * 3.14 - 3/2 * 3.14
    x3[Zrot, 0] = 3.14
    x3[Zrot, 1] = 3 * 3.14

    x4[Xrot, 0] = -2 * 3.14 - 3/2 * 3.14
    x4[Xrot, 1] = -4 * 3.14
    x4[Zrot] = 3 * 3.14

    x_init = InitialGuessList()
    x_init.add(x0, interpolation=InterpolationType.LINEAR)
    x_init.add(x1, interpolation=InterpolationType.LINEAR)
    x_init.add(x2, interpolation=InterpolationType.LINEAR)
    x_init.add(x3, interpolation=InterpolationType.LINEAR)
    x_init.add(x4, interpolation=InterpolationType.LINEAR)

    constraints = ConstraintList()
    constraints.add(ConstraintFcn.SUPERIMPOSE_MARKERS, node=Node.ALL_SHOOTING, min_bound=-.1, max_bound=.1, first_marker='MidMainG', second_marker='CibleMainG', phase=1)
    constraints.add(ConstraintFcn.SUPERIMPOSE_MARKERS, node=Node.ALL_SHOOTING, min_bound=-.1, max_bound=.1, first_marker='MidMainD', second_marker='CibleMainD', phase=1)
#    constraints.add(ConstraintFcn.TIME_CONSTRAINT, node=Node.END, min_bound=0, max_bound=final_time, phase=0)
    constraints.add(ConstraintFcn.TIME_CONSTRAINT, node=Node.END, min_bound=0, max_bound=final_time, phase=1)
    constraints.add(ConstraintFcn.TIME_CONSTRAINT, node=Node.END, min_bound=0, max_bound=final_time, phase=2)
    constraints.add(ConstraintFcn.TIME_CONSTRAINT, node=Node.END, min_bound=0, max_bound=final_time, phase=3)
    constraints.add(ConstraintFcn.TIME_CONSTRAINT, node=Node.END, min_bound=0, max_bound=final_time, phase=4)

    return OptimalControlProgram(
        biorbd_model,
        dynamics,
        n_shooting,
        [final_time/len(biorbd_model)] * len(biorbd_model),
        x_init,
        u_init,
        x_bounds,
        u_bounds,
        objective_functions,
        constraints,
        ode_solver=ode_solver,
        variable_mappings=dof_mappings,
        n_threads=31
    )


def main():
    """
    Prepares and solves an ocp for a 803<. Animates the results
    """

    n_shooting = (40, 100, 100, 100, 40)
    ocp = prepare_ocp("Models/JeCh_TechOpt83.bioMod", n_shooting=n_shooting, final_time=1.87) #######################
    ocp.add_plot_penalty(CostType.ALL)
    ocp.print(to_graph=True)
    solver = Solver.IPOPT(show_online_optim=True, show_options=dict(show_bounds=True))
    solver.set_linear_solver('ma57')  # depend de HSL qui depend de gfortran 7 qui est difficile a obtenir, ultimement facultatif
    solver.set_maximum_iterations(10000)
    solver.set_convergence_tolerance(1e-4)
    sol = ocp.solve(solver)

    temps = time.strftime("%Y-%m-%d-%H%M%S")
    nom = 'sol' + str(n_shooting).replace(', ', '_')
    qs = sol.states[0]['q']
    qdots = sol.states[0]['qdot']
    for i in range(1, len(sol.states)):
        qs = np.hstack((qs, sol.states[i]['q']))
        qdots = np.hstack((qdots, sol.states[i]['qdot']))
    if True:  # switch manuelle
        np.save(f'Solutions/{nom}-{temps}-q.npy', qs)
        np.save(f'Solutions/{nom}-{temps}-qdot.npy', qdots)

    # Print the last solution
    sol.animate(n_frames=-1, show_floor=False)
    #sol.graphs()



if __name__ == "__main__":
    main()
