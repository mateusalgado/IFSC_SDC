# Projeto final - Link de comunicação SDR

Enlace digital simplex ADALM-Pluto (Tx) para RTL-SDR (Rx), em Python. Parte da OOK de referência do professor e acrescenta 2-FSK e DBPSK, número de sequência de 16 bits, CRC-16 e as métricas do enunciado (PER, goodput, BER e banda de 99%).

Enunciado: [projeto_final_sdr.pdf](../../materiais/roteiros/projeto_final_sdr.pdf). Relatório: [PT](relatorio_10_pt.pdf) e [EN](relatorio_10_en.pdf).

## Estrutura

| Caminho | Conteúdo |
|---|---|
| referencia_ook/ | Transmissor e receptor OOK entregues pelo professor, sem alterações |
| sdrlink/quadro.py | Quadro, CRC-8 da referência, CRC-16 e payload PRBS |
| sdrlink/modem.py | Moduladores e detectores de OOK, 2-FSK e DBPSK, com os pulsos alternativos |
| sdrlink/receptor.py | Conversão para banda base, sincronismo, decisão e verificação |
| sdrlink/canal.py, metricas.py | Canal simulado, BER teórica, banda de 99%, PER e goodput |
| sdrlink/radio.py | Parâmetros de bancada e roteiros de ensaio |
| etapa1_executar_referencia.py | Roda o receptor de referência e registra a saída |
| etapa2_modulacoes.py | Formas de onda, espectros, banda de 99% e constelação |
| etapa3_canal.py | BER em AWGN e sensibilidade a fase, offset e temporização |
| etapa4_protocolo.py | Pacotes pelo receptor completo, PER e captura sintética |
| calibrar_ppm.py | Calibração de ppm do RTL-SDR e medida do offset residual |
| tx_pluto.py | Transmissor pelo Pluto, com modo roteiro e ensaio a seco |
| rx_gravar.py, rx_decodificar.py | Gravação IQ do RTL-SDR e decodificação com métricas |
| rx_roteiro.py | Caracterização automática enquanto o Pluto percorre um roteiro |
| ensaio_referencia.py | Ensaio de 60 s, varredura de ganho e tolerância a offset da OOK de referência |
| etapa5_bancada.py | Figuras dos ensaios de bancada |
| ver_sinal.py | Espectro, portadora e envoltória ao vivo |
| figuras/, figuras/en/ | Gráficos em português e em inglês |
| resultados/ | JSON das simulações, da calibração e dos ensaios de bancada |
| capturas/ | Capturas IQ (.cu8, fora do versionamento) e seus resultados |
| registro_ia.md | Registro de uso de IA de todas as etapas |

## Quadro

| Campo | Referência | Projeto |
|---|---|---|
| Preâmbulo alternado | 16 bits | 16 bits |
| Sincronismo Barker-13 | 13 bits | 13 bits |
| Comprimento | 8 bits | 8 bits |
| Número de sequência | não há | 16 bits |
| Payload | 8N bits | 8N bits |
| Verificação | CRC-8 do payload | CRC-16/CCITT de comprimento, sequência e payload |
| Guarda | 16 bits em zero | 16 bits de silêncio |
| Total com 128 bytes | 1085 bits | 1109 bits |

## Ambiente

O ambiente virtual fica em .venv. No macOS, o librtlsdr vem do pacote pyrtlsdr[lib] e o libiio 0.26 foi compilado do código da Analog Devices para dentro do .venv, porque não existe no Homebrew.

    python3 -m venv .venv
    .venv/bin/python -m pip install numpy scipy matplotlib reportlab pylatexenc "pyrtlsdr[lib]" pyadi-iio "pylibiio==0.25"

No Fedora do laboratório valem os scripts do professor em [materiais/codigo_apoio/projeto_final_sdr](../../materiais/codigo_apoio/projeto_final_sdr/).

## Uso

Simulações, sem rádio:

    .venv/bin/python etapa2_modulacoes.py
    .venv/bin/python etapa3_canal.py
    .venv/bin/python etapa4_protocolo.py

Bancada, com o RTL-SDR aquecido por cerca de 10 minutos:

    .venv/bin/python calibrar_ppm.py --ppm 86                 # receptor, com o Pluto transmitindo
    python tx_pluto.py --roteiro basico                       # computador do Pluto
    .venv/bin/python rx_roteiro.py --roteiro basico --ppm 86  # receptor

Um ensaio isolado:

    python tx_pluto.py --esquema fsk --rb 20e3
    .venv/bin/python rx_gravar.py --segundos 30 --ppm 86 --nome fsk_20k
    .venv/bin/python rx_decodificar.py capturas/fsk_20k.cu8 --esquema fsk --rb 20e3 --prbs

O transmissor não depende do receptor. O arquivo tx_kit_pluto.zip leva só tx_pluto.py e os módulos de sdrlink que ele usa, e precisa apenas de numpy e pyadi-iio.

## Regenerar o relatório

    .venv/bin/python gerar_relatorio.py
