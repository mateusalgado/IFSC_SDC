"""Enquadramento do enlace: preâmbulo, sincronismo, cabeçalho, payload e CRC.

Quadro de referência (professor):
    [preâmbulo 16][Barker-13][comprimento 8][payload 8N][CRC-8 8][guarda 16]

Quadro do projeto:
    [preâmbulo 16][Barker-13][comprimento 8][sequência 16][payload 8N][CRC-16 16][guarda 16]

O CRC-16 cobre comprimento, sequência e payload. A guarda é silêncio (amplitude
zero) em todas as modulações e é inserida pelo modulador, não aqui.
"""
import numpy as np

PREAMBULO = np.array([1, 0] * 8, dtype=np.uint8)
BARKER13 = np.array([1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1], dtype=np.uint8)
CABECALHO_SINC = np.concatenate([PREAMBULO, BARKER13])  # 29 bits conhecidos
BITS_GUARDA = 16
BITS_COMPRIMENTO = 8
BITS_SEQUENCIA = 16
BITS_CRC = 16


def crc8(dados: bytes, poli: int = 0x07, inicial: int = 0x00) -> int:
    """CRC-8 da referência (polinômio 0x07), mantido para a auditoria."""
    crc = inicial
    for byte in dados:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ poli) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def _tabela_crc16(poli: int = 0x1021):
    tabela = []
    for i in range(256):
        crc = i << 8
        for _ in range(8):
            crc = ((crc << 1) ^ poli) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
        tabela.append(crc)
    return tabela


_CRC16 = _tabela_crc16()


def crc16(dados: bytes, inicial: int = 0xFFFF) -> int:
    """CRC-16/CCITT-FALSE (polinômio 0x1021, valor inicial 0xFFFF)."""
    crc = inicial
    for byte in dados:
        crc = ((crc << 8) & 0xFFFF) ^ _CRC16[(crc >> 8) ^ byte]
    return crc


def bytes_para_bits(dados: bytes) -> np.ndarray:
    return np.unpackbits(np.frombuffer(dados, dtype=np.uint8))


def bits_para_bytes(bits: np.ndarray) -> bytes:
    return np.packbits(np.asarray(bits, dtype=np.uint8)).tobytes()


def corpo(seq: int, payload: bytes) -> bytes:
    """Bytes protegidos pelo CRC: comprimento, sequência e payload, seguidos do CRC-16."""
    if not 0 <= len(payload) <= 255:
        raise ValueError("O campo de comprimento tem 8 bits: payload de 0 a 255 bytes.")
    protegido = bytes([len(payload)]) + int(seq & 0xFFFF).to_bytes(2, "big") + payload
    return protegido + crc16(protegido).to_bytes(2, "big")


def montar(seq: int, payload: bytes) -> np.ndarray:
    """Bits do quadro, sem a guarda: preâmbulo + Barker + corpo."""
    return np.concatenate([CABECALHO_SINC, bytes_para_bits(corpo(seq, payload))])


def bits_do_quadro(n_payload: int, guarda: bool = True) -> int:
    total = len(CABECALHO_SINC) + BITS_COMPRIMENTO + BITS_SEQUENCIA + 8 * n_payload + BITS_CRC
    return total + (BITS_GUARDA if guarda else 0)


def bits_do_quadro_referencia(n_payload: int) -> int:
    return 16 + 13 + 8 + 8 * n_payload + 8 + 16


def payload_prbs(seq: int, n: int = 128, semente: int = 2026) -> bytes:
    """Payload pseudoaleatório reproduzível por número de sequência (para BER)."""
    return np.random.default_rng([semente, seq]).bytes(n)
