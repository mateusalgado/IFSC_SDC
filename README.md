# Sistemas de Comunicação

Materiais e atividades da disciplina SCM203405, IFSC Florianópolis. O projeto contém nove atividades e o projeto final, seus relatórios em português e inglês e os textos preparados para a série do LinkedIn.

## Relatórios

| Atividade | Tema | Português | Inglês | Arquivos da atividade |
|---|---|---|---|---|
| 01 | Propagação e enlaces | [PT](atividades/01_propagacao_enlaces/relatorio_01_pt.pdf) | [EN](atividades/01_propagacao_enlaces/relatorio_01_en.pdf) | [Pasta](atividades/01_propagacao_enlaces/) |
| 02 | Antenas | [PT](atividades/02_antenas/relatorio_02_pt.pdf) | [EN](atividades/02_antenas/relatorio_02_en.pdf) | [Pasta](atividades/02_antenas/) |
| 03 | Codificação de linha | [PT](atividades/03_codificacao_linha/relatorio_03_pt.pdf) | [EN](atividades/03_codificacao_linha/relatorio_03_en.pdf) | [Pasta](atividades/03_codificacao_linha/) |
| 04 | BASK | [PT](atividades/04_bask/relatorio_04_pt.pdf) | [EN](atividades/04_bask/relatorio_04_en.pdf) | [Pasta](atividades/04_bask/) |
| 05 | BFSK | [PT](atividades/05_bfsk/relatorio_05_pt.pdf) | [EN](atividades/05_bfsk/relatorio_05_en.pdf) | [Pasta](atividades/05_bfsk/) |
| 06 | BPSK | [PT](atividades/06_bpsk/relatorio_06_pt.pdf) | [EN](atividades/06_bpsk/relatorio_06_en.pdf) | [Pasta](atividades/06_bpsk/) |
| 07 | QPSK | [PT](atividades/07_qpsk/relatorio_07_pt.pdf) | [EN](atividades/07_qpsk/relatorio_07_en.pdf) | [Pasta](atividades/07_qpsk/) |
| 08 | 8-PSK | [PT](atividades/08_8psk/relatorio_08_pt.pdf) | [EN](atividades/08_8psk/relatorio_08_en.pdf) | [Pasta](atividades/08_8psk/) |
| 09 | 16-QAM | [PT](atividades/09_16qam/relatorio_09_pt.pdf) | [EN](atividades/09_16qam/relatorio_09_en.pdf) | [Pasta](atividades/09_16qam/) |
| 10 | Projeto final: link SDR | [PT](atividades/10_projeto_final_sdr/relatorio_10_pt.pdf) | [EN](atividades/10_projeto_final_sdr/relatorio_10_en.pdf) | [Pasta](atividades/10_projeto_final_sdr/) |

## Estrutura

- materiais/aulas contém os 12 arquivos de aula, numerados de 01 a 12.
- materiais/listas contém as listas e sua resolução comentada.
- materiais/roteiros contém os enunciados e notebooks originais disponíveis, incluindo o enunciado do projeto final.
- materiais/codigo_apoio contém o pacote original do modelo de microstrip e, em projeto_final_sdr, o código OOK e os scripts de instalação e teste entregues para o projeto final.
- atividades contém os notebooks, códigos, relatórios e figuras de cada atividade. A pasta 10_projeto_final_sdr tem um README próprio, com o código do enlace, as simulações e os ensaios com os rádios.
- linkedin contém os nove textos curtos em inglês e o índice dos anexos.
- scripts contém a renderização padronizada e a exportação dos rótulos dos gráficos em inglês.
- historico contém os relatórios anteriores à padronização e a configuração antiga.

[Índice da série para o LinkedIn](linkedin/README.md)

## Convenção de nomes

As atividades usam dois dígitos e um assunto curto. Os relatórios seguem relatorio_XX_pt e relatorio_XX_en, com versões Markdown editáveis e PDF. As figuras em inglês ficam dentro de figuras/en na respectiva atividade.

O arquivo organizacao_arquivos.json registra os caminhos anteriores e atuais dos arquivos reorganizados.

## Regenerar os PDFs

Instale as dependências Python reportlab, matplotlib e pylatexenc. Execute a partir da raiz do projeto:

    python3 scripts/padronizar_relatorios.py

Esse comando lê os relatórios Markdown existentes e gera os 20 PDFs. Os arquivos gerar_relatorio.py das atividades 3 a 9 também usam a renderização comum.

A exportação dos gráficos em inglês está em scripts/exportar_figuras_en.py e requer numpy, scipy e pandas, além de matplotlib. Ela reutiliza os parâmetros, resultados registrados e sementes dos arquivos existentes. Os notebooks acadêmicos continuam nas pastas das respectivas atividades.

## Revisão editorial e técnica

[Registro dos ajustes e limitações dos resultados](REVISAO.md)

As atividades 7 e 9 ainda têm a folha pessoal de previsões manuscritas como item a completar para a entrega acadêmica. Esse item é separado dos relatórios preparados para divulgação.

O relatório do projeto final é parcial. As etapas com 2-FSK e DBPSK no ar, a otimização e a competição ainda dependem de ensaios com o Pluto. O projeto final ainda não tem texto na série do LinkedIn.
