"""
Atividade 1 - SCM203405 - Alcance e Perda de Percurso em Enlaces Sem Fio
Modulo: ESP32-WROOM-32 (Wi-Fi)

Fonte dos parametros de RF: Espressif Systems, "ESP32-WROOM-32 Datasheet",
Table 18 "TX Power" e Table 19 "RX Sensitivity".
https://documentation.espressif.com/esp32-wroom-32_datasheet_en.pdf

Script de apoio para conferencia dos calculos do relatorio. Nao faz parte
da entrega da atividade.
"""

import math

# --- Parametros extraidos do datasheet -------------------------------------

F_MHZ = 2437.0          # frequencia de operacao (canal 6, meio da faixa 2412-2484 MHz)
GT_DBI = 2.0            # ganho antena Tx (antena PCB integrada, datasheet nao especifica -> 0-3 dBi)
GR_DBI = 2.0            # ganho antena Rx (idem)

# (nome, PTx [dBm], Sensibilidade [dBm])
TAXAS = [
    ("802.11b, 1 Mbps",  19.5, -97.0),
    ("802.11g, 54 Mbps", 14.0, -75.0),
]

# Cenarios indoor: (nome, n, sigma [dB])
CENARIOS_INDOOR = [
    ("Escritorio (obstrucao suave)", 2.4, 9.6),
    ("Escritorio (obstrucao severa)", 3.0, 7.0),
    ("Fabrica LOS - Textil/Quimica", 2.0, 3.0),
    ("Fabrica OBS - Metalurgia", 3.3, 6.8),
]

D0_M = 1.0  # distancia de referencia do modelo log-distancia


# --- Formulas ----------------------------------------------------------------

def pl_max(ptx_dbm, gt_dbi, gr_dbi, sens_dbm):
    """PLmax (dB) = PTx + Gt + Gr - Sensibilidade"""
    return ptx_dbm + gt_dbi + gr_dbi - sens_dbm


def fspl(f_mhz, d_km):
    """FSPL (dB) = 32.44 + 20log10(f_MHz) + 20log10(d_km)"""
    return 32.44 + 20 * math.log10(f_mhz) + 20 * math.log10(d_km)


def alcance_espaco_livre_km(pl_max_db, f_mhz):
    """Isola d_km de FSPL(dB) = 32.44 + 20log10(f) + 20log10(d)"""
    return 10 ** ((pl_max_db - 32.44 - 20 * math.log10(f_mhz)) / 20)


def alcance_indoor_m(pl_max_db, pl_d0_db, n, d0_m=D0_M):
    """Isola d de PL(d) = PL(d0) + 10 n log10(d/d0)  (sigma desprezado no alcance nominal)"""
    return d0_m * 10 ** ((pl_max_db - pl_d0_db) / (10 * n))


# --- Calculo -------------------------------------------------------------------

def main():
    print("=" * 78)
    print("Parametros fixos")
    print("=" * 78)
    print(f"f = {F_MHZ} MHz | Gt = {GT_DBI} dBi | Gr = {GR_DBI} dBi | d0 = {D0_M} m")

    pl_d0_db = fspl(F_MHZ, D0_M / 1000.0)
    print(f"\nPL(d0) = FSPL @ 1 m, {F_MHZ} MHz:")
    print(f"  PL(d0) = 32.44 + 20*log10({F_MHZ}) + 20*log10({D0_M/1000:.6f})")
    print(f"  PL(d0) = {pl_d0_db:.2f} dB")

    resultados_secao3 = []
    print("\n" + "=" * 78)
    print("SECAO 3 - Alcance em espaco livre (LOS)")
    print("=" * 78)
    for nome, ptx, sens in TAXAS:
        plmax = pl_max(ptx, GT_DBI, GR_DBI, sens)
        d_km = alcance_espaco_livre_km(plmax, F_MHZ)
        resultados_secao3.append((nome, ptx, sens, plmax, d_km))
        print(f"\n-- {nome} --")
        print(f"  PLmax = PTx + Gt + Gr - Sensibilidade")
        print(f"  PLmax = {ptx} + {GT_DBI} + {GR_DBI} - ({sens}) = {plmax:.2f} dB")
        print(f"  FSPL(dB) = 32.44 + 20log10(f) + 20log10(d) = PLmax")
        print(f"  {plmax:.2f} = 32.44 + 20log10({F_MHZ}) + 20log10(d_km)")
        print(f"  d = 10^(({plmax:.2f} - 32.44 - 20log10({F_MHZ}))/20)")
        print(f"  d = {d_km:.3f} km = {d_km*1000:.1f} m")

    print("\n" + "=" * 78)
    print("SECAO 4 - Alcance indoor (modelo log-distancia, usando PLmax da taxa 1 Mbps)")
    print("=" * 78)
    plmax_ref = resultados_secao3[0][3]   # PLmax do par 1 Mbps / -97 dBm (potencia maxima real)
    nome_ref = resultados_secao3[0][0]
    print(f"\nPLmax de referencia (potencia maxima, {nome_ref}) = {plmax_ref:.2f} dB")

    resultados_secao4 = []
    for nome, n, sigma in CENARIOS_INDOOR:
        d_m = alcance_indoor_m(plmax_ref, pl_d0_db, n)
        resultados_secao4.append((nome, n, sigma, d_m))
        print(f"\n-- {nome} (n={n}, sigma={sigma} dB) --")
        print(f"  PL(d) = PL(d0) + 10 n log10(d/d0) = PLmax")
        print(f"  {plmax_ref:.2f} = {pl_d0_db:.2f} + 10*{n}*log10(d/{D0_M})")
        print(f"  d = {D0_M} * 10^(({plmax_ref:.2f} - {pl_d0_db:.2f})/(10*{n}))")
        print(f"  d = {d_m:.2f} m")

    print("\n" + "=" * 78)
    print("TABELA-RESUMO FINAL")
    print("=" * 78)
    d_km_ref = resultados_secao3[0][4]
    print(f"{'Cenario':40s} | {'Distancia':>12s} | {'PLmax (dB)':>10s}")
    print("-" * 68)
    print(f"{'Espaco livre (FSPL) - potencia maxima':40s} | {d_km_ref:9.2f} km | {plmax_ref:10.2f}")
    for nome, n, sigma, d_m in resultados_secao4:
        label = f"Indoor - {nome}"
        print(f"{label:40s} | {d_m:9.2f} m  | {plmax_ref:10.2f}")

    print("\n" + "=" * 78)
    print("SECAO 3.2 - Efeito da sensibilidade no alcance (comparacao das 2 taxas)")
    print("=" * 78)
    for nome, ptx, sens, plmax, d_km in resultados_secao3:
        print(f"{nome:20s} PTx={ptx:5.1f} dBm  Sens={sens:6.1f} dBm  "
              f"PLmax={plmax:6.2f} dB  alcance={d_km:8.3f} km")


if __name__ == "__main__":
    main()
