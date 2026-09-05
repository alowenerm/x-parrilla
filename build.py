#!/usr/bin/env python3
"""Regenera /workspace/x-board/index.html desde /workspace/x-posts/queue.json."""
import json, html, shutil, datetime
from pathlib import Path

SRC_Q = Path('/workspace/x-posts/queue.json')
BOARD = Path('/workspace/x-board')
SRC_IMG = Path('/workspace/x-posts/img')

CSS = (BOARD / 'style.css').read_text(encoding='utf-8')

def slot_label(when):
    d, t = when.split(' ')
    day = datetime.date.fromisoformat(d)
    today = datetime.date.today()
    delta = (day - today).days
    if delta == 0: pre = 'Hoy'
    elif delta == 1: pre = 'Mañana'
    elif delta == -1: pre = 'Ayer'
    else: pre = day.strftime('%d/%m')
    return f'{pre} · {t}'

def body_html(text):
    return html.escape(text).replace('\n\n', '<br><br>').replace('\n', '<br>')

def card(item):
    n = item['n']
    posted = item.get('status') == 'posted'
    img = item.get('img_rel') or f"img/{n:02d}.png"
    status = item.get('status', 'pending')
    hold = status == 'hold'
    slot = slot_label(item["when"])
    if hold:
        slot = 'EN ESPERA · ' + slot
    parts = [f'    <article class="card{" hold" if hold else ""}" data-n="{n}" data-status="{status}" id="p{n}">',
             '      <header>',
             f'        <span class="slot">{html.escape(slot)}</span>',
             f'        <span class="meta">#{n} · {html.escape(item["src"])}</span>',
             '      </header>',
             f'      <img src="{img}" alt="post {n}">',
             f'      <p class="copy">{body_html(item["text"])}</p>']
    cite = f'      <p class="cite"><a href="{html.escape(item["url"])}" target="_blank" rel="noopener">cita original</a></p>'
    if posted and item.get('posted_url'):
        cite += f'<p class="cite"><a href="{html.escape(item["posted_url"])}" target="_blank" rel="noopener">ver en X</a></p>'
    parts.append(cite)
    if hold and item.get('note'):
        parts.append(f'      <p class="note">{html.escape(item["note"])}</p>')
    parts.append('      ')
    if not posted:
        parts += ['      <div class="actions">',
                  f'        <button type="button" class="btn ghost" data-act="sacar" data-n="{n}">Sacar de la parrilla</button>',
                  '      </div>',
                  f'      <form class="comment" data-n="{n}">',
                  '        <textarea name="c" rows="2" placeholder="Comentario para ajustar este post…"></textarea>',
                  '        <button type="submit" class="btn">Enviar comentario</button>',
                  '      </form>']
    parts += ['      <p class="hint" hidden></p>', '    </article>']
    return '\n'.join(parts)

SCRIPT = """
function copy(text) {
  navigator.clipboard.writeText(text).catch(() => {});
}
document.querySelectorAll('[data-act="sacar"]').forEach(btn => {
  btn.addEventListener('click', () => {
    const n = btn.dataset.n;
    const card = document.getElementById('p' + n);
    const msg = 'Saca el #' + n + ' de la parrilla';
    copy(msg);
    card.classList.add('out');
    const hint = card.querySelector('.hint');
    hint.hidden = false;
    hint.textContent = 'Copiado: "' + msg + '". Pégalo en el chat para que lo quite de la cola.';
  });
});
document.querySelectorAll('form.comment').forEach(form => {
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const n = form.dataset.n;
    const t = form.c.value.trim();
    if (!t) return;
    const msg = 'Comentario #' + n + ': ' + t;
    copy(msg);
    const hint = form.parentElement.querySelector('.hint');
    hint.hidden = false;
    hint.textContent = 'Copiado: pégalo en el chat y lo aplico al post.';
    form.c.value = '';
  });
});
"""

def main():
    q = json.loads(SRC_Q.read_text(encoding='utf-8'))
    for item in q:
        item['img_rel'] = f"img/{item['n']:02d}.png"
    (BOARD / 'queue.json').write_text(json.dumps(q, ensure_ascii=False, indent=2), encoding='utf-8')

    (BOARD / 'img').mkdir(exist_ok=True)
    used = set()
    for item in q:
        name = f"{item['n']:02d}.png"
        used.add(name)
        dst = BOARD / 'img' / name
        src = SRC_IMG / name
        if src.exists() and (not dst.exists() or src.stat().st_size != dst.stat().st_size):
            shutil.copy2(src, dst)
    for f in (BOARD / 'img').glob('*.png'):
        if f.name not in used:
            f.unlink()
            print('borrada imagen huérfana', f.name)

    pend = sorted([i for i in q if i.get('status') in ('pending','hold')], key=lambda i: i['when'])
    post = sorted([i for i in q if i.get('status') == 'posted'], key=lambda i: i['when'], reverse=True)  # deleted omitted

    def col(items, empty):
        return '\n\n'.join(card(i) for i in items) if items else f'    <p class="empty">{empty}</p>'

    doc = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Parrilla X · @andres_lowener</title>
<style>
{CSS}</style>
</head>
<body>
<header class="top">
  <div>
    <h1>andres@x:~$ parrilla</h1>
    <div class="sub">@andres_lowener · CRT queue · Santiago</div>
  </div>
  <div class="sub">Sacar o comentar acá. El mensaje se copia: pégalo en el chat.</div>
</header>
<main>
  <section class="parrilla">
    <h2>Parrilla · por publicar ({len(pend)})</h2>
    <div class="grid" id="pending">
{col(pend, 'Nada en la parrilla.')}
    </div>
  </section>
  <section>
    <h2>Publicado ({len(post)})</h2>
    <div class="grid" id="posted">
{col(post, 'Nada publicado todavía.')}
    </div>
  </section>
</main>
<script>{SCRIPT}</script>
</body>
</html>
"""
    (BOARD / 'index.html').write_text(doc, encoding='utf-8')
    print(f'index.html: {len(pend)} pendientes, {len(post)} publicados')

if __name__ == '__main__':
    main()
