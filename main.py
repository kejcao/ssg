import sys
from pathlib import Path
from jinja2 import (
    Environment, select_autoescape,
    FileSystemLoader
)
from dateutil.parser import parse, ParserError
import kcdoc

ROOTDIR = Path('/var/www/html/')
POSTS_DIR = ROOTDIR/'posts'
POST_TMPL = 'tmpls/post.j2'
IGNORE = list(Path(ROOTDIR/'tmpls').glob('**/*.j2'))

j2env = Environment(
    loader=FileSystemLoader(ROOTDIR),
    autoescape=select_autoescape()
)

def error(msg):
    print('ssg:', msg, file=sys.stderr)
    sys.exit(1)

def should_update(src, dest):
    return not dest.exists() or src.stat().st_mtime > dest.stat().st_mtime

def render_template(tmpl, data):
    try:
        return j2env.get_template(tmpl).render(data)
    except Exception as e:
        error(f'{tmpl}: {e}.')

def renderj2(posts):
    for src in Path(ROOTDIR).glob('**/*.j2'):
        dest = src.with_suffix('.html')
        if src not in IGNORE and should_update(src, dest):
            dest.write_text(render_template(
                str(src.relative_to(ROOTDIR)),
                { 'posts': posts }
            ))

def render_posts():
    posts = []
    for src in Path(POSTS_DIR).glob('**/*.kcdoc'):
        (folder := src.with_suffix('')).mkdir(exist_ok=True)
        dest = folder/'index.html'

        try:
            content, frontmatter = kcdoc.to_html(
                src.read_text(),
                just_frontmatter=not should_update(src, dest)
            )
        except ValueError as e:
            error(f'{src}: {e}')

        if not { 'title', 'desc', 'date' } <= frontmatter.keys():
            error(f'{src}: misformed frontmatter.')

        try:
            frontmatter['date'] = parse(frontmatter['date']).strftime('%Y-%m-%d')
        except ParserError:
            error(f'{src}: misformed date in frontmatter.')

        frontmatter['slug'] = src.stem
        frontmatter['draft'] = 'draft' in frontmatter

        posts.append(frontmatter)

        if should_update(src, dest):
            dest.write_text(render_template(POST_TMPL,
                { 'post': { 'content': content, **frontmatter } }
            ))

    return posts

def main():
    posts = render_posts()
    renderj2(posts)

if __name__ == '__main__':
    main()
