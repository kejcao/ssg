import sys
from pathlib import Path
from jinja2 import (
    Environment, select_autoescape,
    FileSystemLoader
)
from dateutil.parser import parse
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

def render_template(tmpl, data):
    try:
        return j2env.get_template(tmpl).render(data)
    except Exception as e:
        error(f'{tmpl}: {e}.')

def renderj2(posts):
    for j2 in Path(ROOTDIR).glob('**/*.j2'):
        if j2 not in IGNORE:
            j2.with_suffix('.html').write_text(
                render_template(
                    str(j2.relative_to(ROOTDIR)),
                    { 'posts': posts }
                ))

def render_posts():
    posts = []
    for post in Path(POSTS_DIR).glob('**/*.kcdoc'):
        try:
            content, frontmatter = kcdoc.to_html(post.read_text())
        except ValueError as e:
            error(f'{post}: {e}')

        if not { 'title', 'desc', 'date' } <= frontmatter.keys():
            error(f'{post}: misformed frontmatter.')

        frontmatter['date'] = parse(frontmatter['date']).strftime('%Y-%m-%d')
        frontmatter['slug'] = post.stem
        frontmatter['draft'] = 'draft' in frontmatter

        posts.append(frontmatter)

        folder = post.with_suffix('')
        folder.mkdir(exist_ok=True)
        (folder/'index.html').write_text(
            render_template(POST_TMPL, { 'post': {
                'content': content, **frontmatter
            }}))

    return posts

def main():
    posts = render_posts()
    renderj2(posts)

if __name__ == '__main__':
    main()
