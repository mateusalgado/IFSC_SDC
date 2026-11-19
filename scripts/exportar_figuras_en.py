"""Exporta rótulos em inglês usando parâmetros e resultados já registrados."""
from pathlib import Path
import ast
import contextlib
import io
import json
import os
import sys
import tempfile

os.environ.setdefault('MPLBACKEND', 'Agg')
os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir())/'sdc_matplotlib'))
import matplotlib.pyplot as plt
from matplotlib.text import Text
import numpy as np
from scipy.signal import welch
from scipy.special import erfc

ROOT = Path(__file__).resolve().parents[1]
COLOR = '#285b42'
TRANSLATIONS = {
 'Diagramas de radiacao do dipolo': 'Dipole radiation patterns', 'Dipolo': 'Dipole',
 'Trecho representativo das codificações de linha': 'Representative line-code waveforms',
 'PSD comparando RZ e Manchester': 'RZ and Manchester power spectral density',
 'Sinal recebido após o cabo CAT5e': 'Received waveform after the CAT5e model',
 'QPSK/4 níveis': '4-level polar NRZ', 'Tempo (s)': 'Time (s)', 'Frequência (Hz)': 'Frequency (Hz)',
 'Bits de informação (serial)': 'Serial input bits', 'canal I (bits pares b0, b2, ...)': 'I branch (even-indexed bits)',
 'canal Q (bits ímpares b1, b3, ...)': 'Q branch (odd-indexed bits)',
 'Sinal QPSK s(t)': 'QPSK waveform s(t)', '|S(f)| normalizado': 'Normalized |S(f)|',
 'Espectro de s(t) (FFT com zero-padding)': 'Signal spectrum (zero-padded FFT)',
 'Integrador do canal I (reinicia a cada T)': 'I-branch integrator (reset every T)',
 'Integrador do canal Q (reinicia a cada T)': 'Q-branch integrator (reset every T)',
 'amostra em t = kT': 'sample at t = kT', 'saída do correlator (x₁, x₂)': 'Correlator output (x₁, x₂)',
 'símbolos transmitidos (a₁, a₂)': 'Transmitted symbols (a₁, a₂)', 'φ₁ (em fase)': 'φ₁ (in phase)',
 'φ₂ (quadratura)': 'φ₂ (quadrature)', 'C) Canal com ruído': 'AWGN channel',
 'Constelação 8-PSK (Gray)': 'Gray-coded 8-PSK constellation',
 'usados na sua sequência': 'Used in the sequence', '|S(f)| — seus 4 símbolos': '|S(f)| — four symbols',
 'DEP 8-PSK — sequência longa aleatória [dB]': '8-PSK PSD — long random sequence [dB]',
 'Deslocamento dos símbolos': 'Received symbol displacement', 'ideal': 'Ideal',
 'Bits transmitidos (acima) × demodulados (abaixo)': 'Transmitted bits (top) and recovered bits (bottom)',
 'transmitidos': 'Transmitted', 'demodulados': 'Recovered', 'índice do bit': 'Bit index',
 '8-PSK teórico (Pb)': '8-PSK approximation (Pb)', 'BPSK/QPSK teórico (Pb)': 'BPSK/QPSK theory (Pb)',
 '8-PSK simulado (BER)': '8-PSK simulation (BER)',
 'seu Eb/N0 de referência': 'Reference Eb/N0', 'Probabilidade de erro de bit': 'Bit error probability',
 'Detalhe de S1 a 30 dB': 'Detail around S1 at 30 dB', 'desvio RMS': 'RMS displacement',
 'Constelação 16-QAM com mapeamento Gray': 'Gray-coded 16-QAM constellation',
 'símbolos presentes na sua sequência': 'Symbols present in the sequence',
 'I  (coordenada sobre ψ₁)': 'I coordinate on ψ₁', 'Q  (coordenada sobre ψ₂)': 'Q coordinate on ψ₂',
 'Ramos em fase e em quadratura, e o sinal 16-QAM resultante (6 primeiros símbolos)': 'I/Q branches and 16-QAM waveform (first six symbols)',
 'envoltória': 'Envelope', 'Espectro de s(t) — linhas em f_c e f_c ± Rs': 'Signal spectrum — lines at f_c and f_c ± Rs',
 'dB (normalizado)': 'Normalized power (dB)',
 'Saída dos correlatores — canal ideal (8 primeiros símbolos)': 'Correlator outputs — ideal channel (first eight symbols)',
 'amostra em t = T (saída do correlator)': 'Sample at t = T (correlator output)',
 'x₁ (ramo I)': 'x₁ (I branch)', 'x₂ (ramo Q)': 'x₂ (Q branch)',
 '16-QAM teórica (Gray)': '16-QAM approximation (Gray)',
 '4-QAM/QPSK teórica (referência)': '4-QAM/QPSK theoretical reference',
 '16-QAM simulada': '16-QAM simulation', 'bits/ponto': 'bits/point',
 'Taxa de erro de bit': 'Bit error rate', 'Erro de fase': 'Phase error',
}

def translate_figure(fig):
    for obj in fig.findobj(match=Text):
        text = obj.get_text()
        for old, new in sorted(TRANSLATIONS.items(), key=lambda item: -len(item[0])):
            text = text.replace(old, new)
        obj.set_text(text)

def save(fig, target):
    translate_figure(fig)
    target.parent.mkdir(exist_ok=True, parents=True)
    fig.savefig(target, dpi=180, bbox_inches='tight')
    plt.close(fig)

def activity(number):
    return next((ROOT/'atividades').glob(f'{number:02}_*'))

def functions_from(path, names, scope):
    nodes=[n for n in ast.parse(path.read_text()).body
           if isinstance(n, ast.FunctionDef) and n.name in names]
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),scope)

def early_activities():
    from matplotlib.figure import Figure
    original = Figure.savefig
    # Reexportar gráficos determinísticos das atividades 2 e 3.
    for number in (2,3):
        folder=activity(number)
        out=folder/'figuras/en'
        out.mkdir(parents=True,exist_ok=True)
        def translated_savefig(fig, filename, *args, **kwargs):
            if number==2 and Path(filename).name!='dipolos_comparacao.png':
                return
            translate_figure(fig)
            return original(fig,filename,*args,**kwargs)
        Figure.savefig=translated_savefig
        scope={'np':np,'plt':plt,'welch':welch,'N':89,'OUTPUT':out,'FIG_DIR':out}
        if number==2:
            functions_from(folder/'gerar_atividade2.py',
                           ['dipole_pattern','generate_dipole_figures'],scope)
            scope['generate_dipole_figures']()
        else:
            sys.path.insert(0,str(folder))
            from cat5_eth_channel import cat5_channel
            scope['cat5_channel']=cat5_channel
            names=['unipolar_nrz','unipolar_rz','bipolar_nrz','bipolar_rz',
                   'polar_quaternario_nrz','manchester','generate_figures']
            functions_from(folder/'gerar_relatorio.py',names,scope)
            scope['generate_figures']()
        Figure.savefig=original

    specs={4:('bask',9900,100000,'1101010011010101'),
           5:('bfsk',2400,200000,'0101010101001010'),
           6:('bpsk',4250,200000,'0101010101')}
    recorded={4:([6,10],[.163,.0571]),
              5:([0,2,4,6,8,10,12],[.5,.375,.5,.3125,.6875,.375,.5]),
              6:(list(range(11)),[.0796,.0572,.0374,.021,.0125,.0056,.0015,.001,.0001,.0001,0])}
    for number,(slug,fc,fs,sequence) in specs.items():
        out=activity(number)/'figuras/en'
        bits=np.array(list(sequence),dtype=int)
        samples=fs//1000
        t=np.arange(len(bits)*samples)/fs
        if number==4:
            level=np.repeat(bits*7,samples);wave=level*np.cos(2*np.pi*fc*t)
        elif number==5:
            local=np.tile(np.arange(samples)/fs,len(bits))
            f=np.repeat(np.where(bits==1,fc,2710),samples)
            level=np.repeat(bits,samples);wave=np.cos(2*np.pi*f*local)
        else:
            level=np.repeat(2*bits-1,samples)
            wave=level*np.sqrt(2000)*np.cos(2*np.pi*fc*t)
        fig,ax=plt.subplots(2,1,figsize=(10,5),sharex=True)
        count=min(len(t),6*samples)
        ax[0].plot(t[:count]*1000,level[:count],color=COLOR)
        ax[0].set(ylabel='Input level',title=f'{slug.upper()} signal representation')
        ax[1].plot(t[:count]*1000,wave[:count],color='#ca702d',lw=.8)
        ax[1].set(xlabel='Time (ms)',ylabel='Amplitude')
        fig.tight_layout();save(fig,out/f'sinal_{slug}_tempo.png')
        f=np.fft.rfftfreq(len(wave),1/fs)
        fig,ax=plt.subplots(figsize=(10,4))
        ax.plot(f,np.abs(np.fft.rfft(wave)),color=COLOR)
        ax.set(xlabel='Frequency (Hz)',ylabel='FFT magnitude',title=f'{slug.upper()} amplitude spectrum',
               xlim=(0,2*fc))
        fig.tight_layout();save(fig,out/f'espectro_{slug}.png')
        x,y=recorded[number]
        fine=np.linspace(0,12,250)
        theory=.5*erfc(np.sqrt(10**(fine/10)/(1 if number==6 else 2)))
        fig,ax=plt.subplots(figsize=(8,4.6))
        ax.semilogy(fine,theory,color=COLOR,label='Theoretical reference')
        pos=np.array(y)>0
        ax.semilogy(np.array(x)[pos],np.array(y)[pos],'o-',color='#ca702d',label='Values recorded in the report')
        ax.set(xlabel='Eb/N₀ (dB)',ylabel='BER',title=f'{slug.upper()} recorded BER comparison')
        ax.legend(fontsize=9);ax.grid(True,which='both',alpha=.25)
        fig.tight_layout();save(fig,out/f'ber_{slug}.png')

def notebook_figures(number):
    folder=activity(number);out=folder/'figuras/en'
    # Mesmo código e sementes do notebook existente; apenas a apresentação muda.
    targets={
      7:{'plot_tempo(t, bits':['sinal_qpsk_tempo.png'],
         'plot_espectro(s, fs':['espectro_qpsk.png'],
         'plot_correlador(t':['correladores_qpsk.png'],
         'for ebn0 in':[None,'constelacao_qpsk_6db.png',None]},
      8:{'# ---------------- Look-up table':['constelacao_ideal_8psk.png'],
         '# Espectro de s(t)':['espectro_8psk.png'],
         '# ---------------- Constelação recebida':['decisao_8psk.png'],
         'LISTA_EbN0_dB':['constelacoes_awgn_8psk.png'],
         'def Q(x)':['ber_8psk.png'],
         '# Mesmos bits':[None,'portadora_fracionaria_8psk.png']},
      9:{'def desenha_constelacao':['constelacao_16qam.png'],
         'ramo_I =':['sinal_16qam_tempo.png','espectro_16qam.png'],
         'def correlator':['correladores_16qam.png'],
         'EbN0_vec =':['ber_16qam.png'],
         'def teste_portadora':[None,None,'erro_fase_16qam.png',None]}}
    nb=json.loads(next(folder.glob('atividade_*.ipynb')).read_text())
    scope={'display':lambda value:None}
    for cell in nb['cells']:
        if cell['cell_type']!='code':continue
        source=''.join(cell['source'])
        if 'from ipywidgets import' in source:continue
        chosen=next((files for prefix,files in targets[number].items() if source.startswith(prefix)),[])
        state={'index':0}
        def show():
            for fignum in plt.get_fignums():
                fig=plt.figure(fignum);idx=state['index'];state['index']+=1
                if idx<len(chosen) and chosen[idx]:
                    save(fig,out/chosen[idx])
                else:plt.close(fig)
        plt.show=show
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(source,'existing_notebook','exec'),scope)
    print(f'Activity {number} figures exported.')

if __name__=='__main__':
    early_activities()
    for number in (7,8,9):notebook_figures(number)
