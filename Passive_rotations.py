
import biorbd
import numpy as np
import matplotlib.pyplot as plt
import scipy.integrate
from IPython import embed
import bioviz

"""
Ce code a été écrit pout faire les simulations pour Antoine, 
mais il pourra être modifié pour apporter d'autres infos utiles avec d'autres anthropo comme base.
Attention, ici on considere des mouvements des joints à vitesse constante (Qddot_J = 0).
C'est surement overkill d'utiliser un KR4 à 100 noeuds pour des mouvements à vitesse constante, mais bon
"""
#
# Physique
#
def Quintic(t, Ti, Tj, Qi, Qj):  # Quintic est bonne
    if t < Ti:
        t = Ti
    elif t > Tj:
        t = Tj

    tp0 = Tj - Ti
    tp1 = (t - Ti) / tp0

    tp2 = tp1**3 * (6 * tp1**2 - 15 * tp1 + 10)
    tp3 = Qj - Qi  # x1 x2
    tp4 = t - Ti
    tp5 = Tj - t

    p = Qi + tp3 * tp2
    v = 30 * tp3 * tp4**2 * tp5**2 / tp0**5
    a = 60 * tp3 * tp4 * tp5 * (Tj + Ti - 2 * t) / tp0**5
    return p, v, a

def dynamics_root(m, X, Qddot_J):
    Q = X[:m.nbQ()]
    Qdot = X[m.nbQ():]
    Qddot = np.hstack((np.zeros((6,)), Qddot_J)) #qddot2
    NLEffects = m.InverseDynamics(Q, Qdot, Qddot).to_array()
    mass_matrix = m.massMatrix(Q).to_array()
    # Qddot_R = np.linalg.inv(mass_matrix[:6, :6]) @ NLEffects[:6]
    Qddot_R = np.linalg.solve(mass_matrix[:6, :6], -NLEffects[:6])
    Xdot = np.hstack((Qdot, Qddot_R, Qddot_J))
    return Xdot, Qddot_R

# N1 = m.NLE_effects(q, qdot)
# Qddot_R = inv(mass_matrix[:6, :6]) @ (-N1-mass_matrix[:6, 6:] @ Qddot_J)

def bras_en_haut(m, x0, t, T0, Tf, Q0, Qf, qddot_j: list=None, qddot_r: list=None):
    Qddot_J = np.zeros(m.nbQ() - m.nbRoot())
    if qddot_j is not None:  # c'est pas beau mais je veux sortir cette information de la fonction
        qddot_j.append(Qddot_J)

    x, Qddot_R = dynamics_root(m, x0, Qddot_J)
    if qddot_r is not None:
        qddot_r.append(Qddot_J)
    return x

def bras_descendent(m, x0, t, T0, Tf, Q0, Qf, qddot_j: list=None, qddot_r: list=None):
    global GAUCHE
    global DROITE
    Kp = 10.
    Kv = 3.
    p, v, a = Quintic(t, T0, Tf, Q0, Qf)
    Qddot_J = np.zeros(m.nbQ() - m.nbRoot())
    Qddot_J[GAUCHE - m.nbRoot()] = a + Kp * (p - x0[GAUCHE]) + Kv * (v - x0[m.nbQ() + GAUCHE])
    Qddot_J[DROITE - m.nbRoot()] = -a + Kp * (-p - x0[DROITE]) + Kv * (-v - x0[m.nbQ() + DROITE])

    if qddot_j is not None:
        qddot_j.append(Qddot_J)

    x, Qddot_R = dynamics_root(m, x0, Qddot_J)
    if qddot_r is not None:
        qddot_r.append(Qddot_J)
    return x

def bras_gauche_descend(m, x0, t, T0, Tf, Q0, Qf, qddot_j: list=None, qddot_r: list=None):
    global GAUCHE
    Kp = 10.
    Kv = 3.
    p, v, a = Quintic(t, T0, Tf, Q0, Qf)
    Qddot_J = np.zeros(m.nbQ() - m.nbRoot())
    Qddot_J[GAUCHE - m.nbRoot()] = a + Kp * (p - x0[GAUCHE]) + Kv * (v - x0[m.nbQ() + GAUCHE])
    if qddot_j is not None:
        qddot_j.append(Qddot_J)

    x, Qddot_R = dynamics_root(m, x0, Qddot_J)
    if qddot_r is not None:
        qddot_r.append(Qddot_J)
    return x

def bras_droit_descend(m, x0, t, T0, Tf, Q0, Qf, qddot_j: list=None, qddot_r: list=None):
    global DROITE
    Kp = 10.
    Kv = 3.
    p, v, a = Quintic(t, T0, Tf, Q0, Qf)
    Qddot_J = np.zeros(m.nbQ() - m.nbRoot())
    Qddot_J[DROITE - m.nbRoot()] = -a + Kp * (-p - x0[DROITE]) + Kv * (-v - x0[m.nbQ() + DROITE])
    if qddot_j is not None:
        qddot_j.append(Qddot_J)

    x, Qddot_R = dynamics_root(m, x0, Qddot_J)
    if qddot_r is not None:
        qddot_r.append(Qddot_J)
    return x

#
# Visualisation
#
def plot_Q_Qdot_bras(m, t, X_tous, Qddot):
    nb_q = m.nbQ()
    QbrasD = X_tous[:, 15]
    QbrasG = X_tous[:, 24]
    QdotbrasD = X_tous[:, nb_q + 15]
    QdotbrasG = X_tous[:, nb_q + 24]
    QddotbrasD = Qddot[:, 15-m.nbRoot()]
    QddotbrasG = Qddot[:, 24-m.nbRoot()]

    fig, ((axQG, axQD), (axQdG, axQdD), (axQddG, axQddD)) = plt.subplots(3, 2)
    axQD.plot(t, QbrasD)
    axQD.set_title("Q droit")
    axQG.plot(t, QbrasG)
    axQG.set_title("Q gauche")
    axQdD.plot(t, QdotbrasD)
    axQdD.set_title("Qdot droit")
    axQdG.plot(t, QdotbrasG)
    axQdG.set_title("Qdot gauche")
    axQddD.plot(t, QddotbrasD)
    axQddD.set_title("Qddot droit")
    axQddG.plot(t, QddotbrasG)
    axQddG.set_title("Qddot gauche")

    plt.tight_layout()
    plt.show(block=False)

def plot_Q_Qdot_bassin(m, t, X_tous, Qddot_R):
    nb_q = m.nbQ()

    QX = X_tous[:, 0]
    QY = X_tous[:, 1]
    QZ = X_tous[:, 2]
    QrotX = X_tous[:, 3]
    QrotY = X_tous[:, 4]
    QrotZ = X_tous[:, 5]

    fig, (axX, axY, axZ) = plt.subplots(3, 1)
    axX.plot(t, QX)
    axX.set_title("Q X")
    axY.plot(t, QY)
    axY.set_title("Q Y")
    axZ.plot(t, QZ)
    axZ.set_title("Q Z")

    figrot, (axrotX, axrotY, axrotZ) = plt.subplots(3, 1)
    axrotX.plot(t, QrotX)
    axrotX.set_title("Q Rot X")
    axrotY.plot(t, QrotY)
    axrotY.set_title("Q Rot Y")
    axrotZ.plot(t, QrotZ)
    axrotZ.set_title("Q Rot Z")

    # vitesses
    QdotX = X_tous[:, nb_q + 0]
    QdotY = X_tous[:, nb_q + 1]
    QdotZ = X_tous[:, nb_q + 2]
    QdotrotX = X_tous[:, nb_q + 3]
    QdotrotY = X_tous[:, nb_q + 4]
    QdotrotZ = X_tous[:, nb_q + 5]

    figdot, (axdotX, axdotY, axdotZ) = plt.subplots(3, 1)
    axdotX.plot(t, QdotX)
    axdotX.set_title("Qdot X")
    axdotY.plot(t, QdotY)
    axdotY.set_title("Qdot Y")
    axdotZ.plot(t, QdotZ)
    axdotZ.set_title("Qdot Z")

    figdotrot, (axdotrotX, axdotrotY, axdotrotZ) = plt.subplots(3, 1)
    axdotrotX.plot(t, QdotrotX)
    axdotrotX.set_title("Qdot Rot X")
    axdotrotY.plot(t, QdotrotY)
    axdotrotY.set_title("Qdot Rot Y")
    axdotrotZ.plot(t, QdotrotZ)
    axdotrotZ.set_title("Qdot Rot Z")

    # accelerations
    QddotX = Qddot_R[:, 0]
    QddotY = Qddot_R[:, 1]
    QddotZ = Qddot_R[:, 2]
    QddotrotX = Qddot_R[:, 3]
    QddotrotY = Qddot_R[:, 4]
    QddotrotZ = Qddot_R[:, 5]

    figdot, (axddotX, axddotY, axddotZ) = plt.subplots(3, 1)
    axddotX.plot(t, QddotX)
    axddotX.set_title("Qddot X")
    axddotY.plot(t, QddotY)
    axddotY.set_title("Qddot Y")
    axddotZ.plot(t, QddotZ)
    axddotZ.set_title("Qddot Z")

    figddotrot, (axddotrotX, axddotrotY, axddotrotZ) = plt.subplots(3, 1)
    axddotrotX.plot(t, QddotrotX)
    axddotrotX.set_title("Qddot Rot X")
    axddotrotY.plot(t, QddotrotY)
    axddotrotY.set_title("Qddot Rot Y")
    axddotrotZ.plot(t, QddotrotZ)
    axddotrotZ.set_title("Qddot Rot Z")

    plt.tight_layout()
    plt.show(block=False)


#
# Simulation
#
def simuler(nom, m, N, t0, tf, T0, Tf, Q0, Qf, X0, action_bras, viz=False):
    m.setGravity(np.array((0, 0, 0)))
    t, dt = np.linspace(t0, tf, num=N, retstep=True)

    Qddot_J = []
    Qddot_R = []

    func = lambda t, y: action_bras(m, y, t, T0, Tf, Q0, Qf, qddot_j=Qddot_J, qddot_r=Qddot_R)

    r = scipy.integrate.ode(func).set_integrator('dop853').set_initial_value(X0, t0)
    X_tous = X0
    while r.successful() and r.t < tf:  # inspire de la doc de scipy [https://docs.scipy.org/doc/scipy-0.13.0/reference/generated/scipy.integrate.ode.html]
        r.integrate(r.t + dt)
        X_tous = np.vstack((X_tous, r.y))

    print(f"{nom}")
    print(f"Salto : {X_tous[-1, 3] / 2 / np.pi}\nTilt : {X_tous[-1, 4] / 2 / np.pi}\nTwist : {X_tous[-1, 5] / 2 / np.pi}\n")

    if viz:
        # Qddot_J = np.array(Qddot_J)
        # Qddot_R = np.array(Qddot_R)
        # plot_Q_Qdot_bras(m_JeCh, t, X_tous, Qddot_J)
        # plot_Q_Qdot_bassin(m_JeCh, t, X_tous, Qddot_R)

        b = bioviz.Viz(model_path_JeCh, show_floor=False)
        b.load_movement(X_tous[:, :m_JeCh.nbQ()].T)
        b.exec()

N = 100
model_path_JeCh = "Models/JeCh_pr.bioMod"
model_path_SaMi = "Models/SaMi_pr.bioMod"
m_JeCh = biorbd.Model(model_path_JeCh)
m_SaMi = biorbd.Model(model_path_SaMi)

GAUCHE = 24  # 42 -> 24; 10 -> 9
DROITE = 15  # 42 -> 15; 10 -> 7

t0 = 0.
tf = 1.
T0 = 0.
Tf = .2
Q0 = 2.9
Qf = .18

# JeCh
# correction pour la translation
X0 = np.zeros(m_JeCh.nbQ() * 2)
X0[DROITE] = -Q0
X0[GAUCHE] = Q0

CoM_func = m_JeCh.CoM(X0[:m_JeCh.nbQ()]).to_array()
bassin = m_JeCh.globalJCS(0).to_array()
QCoM = CoM_func.reshape(1, 3)
Qbassin = bassin[-1, :3]
r = QCoM - Qbassin

X0[m_JeCh.nbQ() + 3] = 2 * np.pi  # Salto rot
X0[m_JeCh.nbQ():m_JeCh.nbQ()+3] = X0[m_JeCh.nbQ():m_JeCh.nbQ() + 3] + np.cross(r, X0[m_JeCh.nbQ()+3:m_JeCh.nbQ()+6])

simuler("JeCh", m_JeCh, N, t0, tf, T0, Tf, Q0, Qf, X0, action_bras=bras_en_haut)
simuler("JeCh", m_JeCh, N, t0, tf, T0, Tf, Q0, Qf, X0, action_bras=bras_descendent)
simuler("JeCh", m_JeCh, N, t0, tf, T0, Tf, Q0, Qf, X0, action_bras=bras_gauche_descend)
simuler("JeCh", m_JeCh, N, t0, tf, T0, Tf, Q0, Qf, X0, action_bras=bras_droit_descend)

# SaMi
# correction pour la translation
X0 = np.zeros(m_SaMi.nbQ() * 2)
X0[DROITE] = -Q0
X0[GAUCHE] = Q0

CoM_func = m_SaMi.CoM(X0[:m_SaMi.nbQ()]).to_array()
bassin = m_SaMi.globalJCS(0).to_array()
QCoM = CoM_func.reshape(1, 3)
Qbassin = bassin[-1, :3]
r = QCoM - Qbassin

X0[m_SaMi.nbQ() + 3] = 2 * np.pi  # Salto rot
X0[m_SaMi.nbQ():m_SaMi.nbQ()+3] = X0[m_SaMi.nbQ():m_SaMi.nbQ() + 3] + np.cross(r, X0[m_SaMi.nbQ()+3:m_SaMi.nbQ()+6])

simuler("SaMi", m_SaMi, N, t0, tf, T0, Tf, Q0, Qf, X0, action_bras=bras_en_haut)
simuler("SaMi", m_SaMi, N, t0, tf, T0, Tf, Q0, Qf, X0, action_bras=bras_descendent)
simuler("SaMi", m_SaMi, N, t0, tf, T0, Tf, Q0, Qf, X0, action_bras=bras_gauche_descend)
simuler("SaMi", m_SaMi, N, t0, tf, T0, Tf, Q0, Qf, X0, action_bras=bras_droit_descend)

