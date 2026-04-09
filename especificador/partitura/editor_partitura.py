#!/usr/bin/env python3
"""
EDITOR DE PARTITURA · JOGO DA VIDA
6 linhas pentagramáticas · canal D · Mouse 3D
Pendurar objetos nas linhas em cada compasso
"""

import json, os, sys
from PIL import Image, ImageDraw

# ── CONSTANTES ──────────────────────────────────────────────
LINHAS   = ['X', 'Y', 'Z', 'rotX', 'rotY', 'rotZ']
LINHA_R  = {'X':0.95,'Y':0.78,'Z':0.60,'rotX':0.42,'rotY':0.24,'rotZ':0.10}
LINHA_COR_RGB = {
    'X':    (20,100,180),
    'Y':    (20,130, 80),
    'Z':    (80,130, 40),
    'rotX': (140,110,30),
    'rotY': (170, 80,25),
    'rotZ': (180, 40,20),
}
LINHA_CLASSE = {
    'X':   'translação H · tik-tak',
    'Y':   'translação V · alto/baixo',
    'Z':   'profundidade · fundo/frente',
    'rotX':'pitch · inclinação',
    'rotY':'yaw · orientação',
    'rotZ':'roll · rotação pura',
}

SISTEMAS = {
    '0': ('zodíaco',  ['♈','♉','♊','♋','♌','♍','♎','♏','♐','♑','♒','♓']),
    '1': ('meses',    ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez']),
    '2': ('horas',    ['01h','02h','03h','04h','05h','06h','07h','08h','09h','10h','11h','12h']),
    '3': ('notas',    ['dó','ré','mi','fá','sol','lá','si','dó#','ré#','fá#','sol#','lá#']),
    '4': ('arcanos',  ['I','II','III','IV','V','VI','VII','VIII','IX','X','XI','XII']),
    '5': ('formas',   ['○','△','□','◇','∞','✦','⬡','↔','⟶','⟵','↑','↓']),
    '6': ('texto',    None),  # livre
}

SAVE_FILE = '/home/claude/partitura_estado.json'

# ── ESTADO ──────────────────────────────────────────────────
def estado_vazio():
    return {
        'compassos': {str(i): {
            'linha': None,
            'objetos': [],  # lista de {'tipo':str, 'valor':str, 'sistema':str}
            'dur': 700,
            'tiktok': 'tik' if i <= 6 else 'tak',
            'nota': '',
        } for i in range(1,13)}
    }

def carregar():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE) as f:
            return json.load(f)
    return estado_vazio()

def salvar(estado):
    with open(SAVE_FILE,'w') as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)

# ── RENDER ───────────────────────────────────────────────────
def render_gif(estado, out='/home/claude/partitura_edit.gif'):
    W, H = 820, 580
    MARGIN_L, MARGIN_R, MARGIN_T, MARGIN_B = 120, 30, 60, 55
    PANEL_W = 195

    BG=(248,246,240); GRID=(215,212,205); TEXT=(55,53,48)
    TEXT2=(130,127,120); TEXT3=(175,172,165); PANEL=(238,235,228); BORD=(205,202,195)

    def ly(l):
        idx = LINHAS.index(l)
        return MARGIN_T + idx*((H-MARGIN_T-MARGIN_B)//(len(LINHAS)-1))

    def cx(i):
        return MARGIN_L + (i-1)*((W-MARGIN_L-MARGIN_R-PANEL_W)//11)

    frames, durs = [], []

    for fi in range(1,13):
        c = estado['compassos'][str(fi)]
        img = Image.new('RGB',(W,H),BG)
        draw = ImageDraw.Draw(img)

        # título
        draw.text((MARGIN_L,10),"partitura · 6 linhas · canal D · Mouse 3D",fill=TEXT2)

        # 6 linhas
        x_end = W-MARGIN_R-PANEL_W-12
        for l in LINHAS:
            yy = ly(l)
            cor = LINHA_COR_RGB[l]
            cdim = tuple(min(255,c2+110) for c2 in cor)
            draw.line([(MARGIN_L-55,yy),(x_end,yy)], fill=cdim, width=1)
            draw.text((4,yy-7), l, fill=cor)
            draw.text((4,yy+4), LINHA_CLASSE[l][:12], fill=TEXT3)
            draw.text((MARGIN_L-53,yy-7), f"r={LINHA_R[l]:.2f}", fill=cdim)

        # divisor tik/tak
        xd = (cx(6)+cx(7))//2
        draw.line([(xd,MARGIN_T-25),(xd,H-MARGIN_B+12)], fill=GRID, width=1)
        draw.text((MARGIN_L,H-MARGIN_B+16),"← tik",fill=TEXT3)
        draw.text((xd+6,H-MARGIN_B+16),"tak →",fill=TEXT3)

        # grade vertical
        for i in range(1,13):
            draw.line([(cx(i),MARGIN_T-18),(cx(i),H-MARGIN_B+10)],fill=(232,230,224),width=1)
            draw.text((cx(i)-4,H-MARGIN_B+4),str(i),fill=TEXT3)

        # todos os compassos
        for i in range(1,13):
            ci = estado['compassos'][str(i)]
            if not ci['linha'] or ci['linha'] not in LINHAS:
                continue
            xx, yy = cx(i), ly(ci['linha'])
            cor = LINHA_COR_RGB[ci['linha']]
            cdim = tuple(min(255,c2+100) for c2 in cor)
            is_cur = (i == fi)

            # linha ao anterior
            if i > 1:
                cp = estado['compassos'][str(i-1)]
                if cp['linha'] and cp['linha'] in LINHAS:
                    ppx, ppy = cx(i-1), ly(cp['linha'])
                    draw.line([(ppx,ppy),(xx,yy)], fill=(cor if is_cur else cdim), width=(2 if is_cur else 1))

            # ponto
            r = 11 if is_cur else 6
            fill = cor if is_cur else cdim
            outline = (80,78,72) if is_cur else GRID
            draw.ellipse([(xx-r,yy-r),(xx+r,yy+r)], fill=fill, outline=outline)

            # objetos pendurados
            for oi, obj in enumerate(ci['objetos'][:4]):
                oy = yy - 28 - oi*14
                draw.text((xx-5, oy), obj['valor'], fill=(cor if is_cur else cdim))

            # número
            draw.text((xx-4, yy+13), str(i), fill=(cor if is_cur else TEXT3))

            # nota livre
            if ci['nota']:
                draw.text((xx-20, yy-50), ci['nota'][:8], fill=TEXT3)

        # painel lateral — compasso atual
        c = estado['compassos'][str(fi)]
        px = W-PANEL_W-MARGIN_R+8
        draw.rectangle([(px-6,38),(W-4,H-38)], fill=PANEL, outline=BORD)
        draw.text((px,46), f"compasso {fi}/12", fill=TEXT)

        if c['linha'] and c['linha'] in LINHAS:
            cor = LINHA_COR_RGB[c['linha']]
            draw.text((px,60), f"linha  {c['linha']}", fill=cor)
            draw.text((px,74), LINHA_CLASSE[c['linha']][:20], fill=TEXT2)
            draw.text((px,88), f"r={LINHA_R[c['linha']]:.2f}", fill=TEXT2)
        else:
            draw.text((px,60), "linha: —", fill=TEXT3)

        draw.text((px,104), c['tiktok'], fill=TEXT2)
        draw.text((px,118), f"{c['dur']}ms", fill=TEXT2)

        if c['nota']:
            draw.text((px,132), c['nota'][:22], fill=TEXT2)

        # objetos
        draw.text((px,150), "objetos:", fill=TEXT3)
        for oi,obj in enumerate(c['objetos'][:5]):
            cor2 = LINHA_COR_RGB.get(c['linha'],(120,120,110)) if c['linha'] else (120,120,110)
            draw.text((px, 163+oi*14), f"  {obj['valor']}  {obj['tipo']}", fill=cor2)

        frames.append(img)
        durs.append(c['dur'])

    frames[0].save(out, save_all=True, append_images=frames[1:],
                   duration=durs, loop=0, optimize=False)
    return out

# ── CLI ──────────────────────────────────────────────────────
def clear(): print('\n'*2)

def mostrar_estado(estado):
    print("\n╔═══ PARTITURA · 12 COMPASSOS ══════════════════════════════╗")
    for i in range(1,13):
        c = estado['compassos'][str(i)]
        tt = 'tik' if i<=6 else 'tak'
        l  = c['linha'] or '—'
        objs = ' '.join(o['valor'] for o in c['objetos']) or '—'
        nota = f" [{c['nota']}]" if c['nota'] else ''
        cur = '►' if False else ' '
        print(f"  {cur}{i:02d} {tt} │ {l:<6} │ r={LINHA_R.get(l,0):.2f} │ {objs:<20}{nota}")
    print("╚════════════════════════════════════════════════════════════╝")

def menu_principal():
    print("""
─── MENU ────────────────────────────────────
  [1-12]  editar compasso
  [v]     ver partitura completa
  [g]     gerar GIF
  [l]     listar todos objetos
  [z]     zerar tudo
  [s]     salvar
  [q]     sair
─────────────────────────────────────────────""")

def menu_linha():
    print("\n  Escolha a linha (face do cubo):")
    for i,l in enumerate(LINHAS):
        print(f"  [{i+1}] {l:<6} r={LINHA_R[l]:.2f}  {LINHA_CLASSE[l]}")
    print("  [0] manter atual")

def menu_sistema():
    print("\n  Sistema simbólico:")
    for k,(nome,_) in SISTEMAS.items():
        print(f"  [{k}] {nome}")

def editar_compasso(estado, num):
    c = estado['compassos'][str(num)]
    tt = 'tik' if num<=6 else 'tak'
    print(f"\n─── COMPASSO {num}/12 · {tt} ─────────────────────────")
    print(f"  linha atual: {c['linha'] or '—'}")
    print(f"  objetos:     {[o['valor'] for o in c['objetos']] or '—'}")
    print(f"  duração:     {c['dur']}ms")
    print(f"  nota:        {c['nota'] or '—'}")
    print("""
  [l] definir linha
  [a] adicionar objeto
  [r] remover objeto
  [d] duração
  [n] nota livre
  [x] limpar tudo
  [v] voltar""")

    while True:
        op = input("  > ").strip().lower()

        if op == 'v':
            break

        elif op == 'l':
            menu_linha()
            idx = input("  > ").strip()
            if idx == '0':
                pass
            elif idx.isdigit() and 1<=int(idx)<=6:
                c['linha'] = LINHAS[int(idx)-1]
                print(f"  ✓ linha → {c['linha']}")

        elif op == 'a':
            menu_sistema()
            sk = input("  sistema > ").strip()
            if sk not in SISTEMAS:
                print("  inválido")
                continue
            nome, simbolos = SISTEMAS[sk]
            if simbolos:
                print(f"\n  {nome}:")
                for i,s in enumerate(simbolos):
                    print(f"  [{i+1:02d}] {s}", end='  ')
                    if (i+1)%4==0: print()
                print()
                si = input("  símbolo (num ou texto livre) > ").strip()
                if si.isdigit() and 1<=int(si)<=len(simbolos):
                    val = simbolos[int(si)-1]
                else:
                    val = si
            else:
                val = input("  texto livre > ").strip()
            if val:
                c['objetos'].append({'tipo':nome,'valor':val,'sistema':sk})
                print(f"  ✓ adicionado: {val}")

        elif op == 'r':
            if not c['objetos']:
                print("  nenhum objeto")
                continue
            for i,o in enumerate(c['objetos']):
                print(f"  [{i+1}] {o['valor']}  ({o['tipo']})")
            ri = input("  remover (num) > ").strip()
            if ri.isdigit() and 1<=int(ri)<=len(c['objetos']):
                rem = c['objetos'].pop(int(ri)-1)
                print(f"  ✓ removido: {rem['valor']}")

        elif op == 'd':
            d = input(f"  duração em ms [{c['dur']}] > ").strip()
            if d.isdigit():
                c['dur'] = int(d)
                print(f"  ✓ duração → {c['dur']}ms")

        elif op == 'n':
            n = input(f"  nota livre [{c['nota'] or '—'}] > ").strip()
            c['nota'] = n
            print(f"  ✓ nota → {n}")

        elif op == 'x':
            c['linha'] = None
            c['objetos'] = []
            c['nota'] = ''
            print("  ✓ compasso limpo")

        else:
            print("  opção inválida")

def main():
    print("╔════════════════════════════════════════════════════════════╗")
    print("║  EDITOR DE PARTITURA · JOGO DA VIDA · canal D · Mouse 3D  ║")
    print("╚════════════════════════════════════════════════════════════╝")

    estado = carregar()

    while True:
        mostrar_estado(estado)
        menu_principal()
        op = input("  > ").strip().lower()

        if op == 'q':
            salvar(estado)
            print("  salvo. até logo.")
            break

        elif op == 's':
            salvar(estado)
            print("  ✓ salvo")

        elif op == 'v':
            mostrar_estado(estado)

        elif op == 'g':
            print("  gerando GIF...")
            out = render_gif(estado, '/home/claude/partitura_edit.gif')
            # copia para outputs
            import shutil
            shutil.copy(out, '/mnt/user-data/outputs/partitura_editada.gif')
            print(f"  ✓ GIF salvo: /mnt/user-data/outputs/partitura_editada.gif")

        elif op == 'l':
            print("\n  TODOS OS OBJETOS:")
            for i in range(1,13):
                c = estado['compassos'][str(i)]
                if c['objetos']:
                    objs = ', '.join(f"{o['valor']}({o['tipo']})" for o in c['objetos'])
                    print(f"  compasso {i:02d} [{c['linha'] or '—'}]: {objs}")

        elif op == 'z':
            conf = input("  zerar tudo? [s/n] > ").strip().lower()
            if conf == 's':
                estado = estado_vazio()
                salvar(estado)
                print("  ✓ zerado")

        elif op.isdigit() and 1<=int(op)<=12:
            editar_compasso(estado, int(op))
            salvar(estado)

        else:
            print("  opção inválida")

if __name__ == '__main__':
    main()
