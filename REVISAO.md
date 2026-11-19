# Revisão dos relatórios

A padronização utiliza os relatórios existentes como base. Foram uniformizados títulos, autoria, tipografia, cabeçalhos, tabelas, fórmulas, legendas e nomes dos arquivos. As versões em inglês acompanham o conteúdo e os resultados registrados. Os arquivos anteriores estão em historico/relatorios_antes_padronizacao.

## Ajustes técnicos

- Atividade 1. A referência de potência do datasheet v3.7 é a Tabela 17. O modelo log-distância usa uma variável aleatória de shadowing, cujo desvio-padrão é σ. Os alcances são estimativas de modelo com ganhos assumidos e margem zero. Uma margem finita não garante disponibilidade absoluta.
- Atividade 2. O padrão normalizado do dipolo muito curto varia pouco com o comprimento. Um dipolo de um comprimento de onda no modelo usado não ganha automaticamente lóbulos adicionais. A comparação das antenas 1 e 2 mantém frequência e espessura iguais.
- Atividade 3. A semente do gerador de figuras é 789. O primeiro nulo positivo NRZ é Rb, enquanto a largura bilateral entre nulos é 2Rb. Manchester possui nulo em DC e nos múltiplos pares de Rb. O FIR do cabo tem atraso de 256 amostras e usa extrapolação acima de 100 MHz.
- Atividade 4. A amplitude informada é 7 V, enquanto o texto antigo usava 5 V em algumas contas. A energia do estado ligado é aproximadamente 0,0245 J e a energia média para bits equiprováveis é metade disso. Os valores históricos de BER foram mantidos e a conclusão passou a identificar a inconsistência de normalização.
- Atividade 5. A energia do sinal gerado não corresponde ao Eb usado para gerar o ruído. O teste histórico usa somente 16 bits por ponto. A conclusão explicita essas limitações, sem atribuir toda a divergência à separação de frequências.
- Atividade 6. A energia amostral da referência varia ligeiramente entre janelas. O valor de 42 kHz da rotina histórica não representa uma largura de banda de 99% válida. A largura entre nulos do pulso continua sendo 2 kHz.
- Atividades 7 a 9. Os resultados quantitativos e os cenários dos relatórios existentes foram preservados.
- Projeto final. O relatório 10 é parcial e separa o que foi simulado do que foi medido. A recepção no ar cobre apenas a OOK de referência. A banda de 99% medida ficou 24% acima da simulada, sem causa confirmada. A distância e as antenas dos ensaios não foram registradas. O transmissor das novas modulações foi testado apenas a seco.

## Gráficos

As figuras em português vêm dos relatórios existentes. Os rótulos das versões em inglês foram reexportados com os mesmos parâmetros. Para ASK, BFSK e BPSK, as curvas de BER em inglês usam os valores numéricos registrados nos relatórios. Os gráficos de forma de onda em inglês foram reconstruídos com os parâmetros e as sequências descritos no texto.

## Escopo da divulgação

Cada postagem acompanha um relatório técnico em inglês. Os textos apresentam os trabalhos como simulações ou cálculos e identificam a limitação de BER das atividades 4 e 5. Nenhuma postagem foi enviada à plataforma nesta organização.
