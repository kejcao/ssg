import sys
from pathlib import Path
from jinja2 import (
    Environment,
    select_autoescape,
    FileSystemLoader
)
from dateutil.parser import isoparse
import kcdoc

ROOTDIR = Path('/srv/http/')
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

def renderj2():
    for j2 in Path(ROOTDIR).glob('**/*.j2'):
        if j2 not in IGNORE:
            j2.with_suffix('.html').write_text(
                j2env.get_template(
                    str(j2.relative_to(ROOTDIR))
                ).render()
            )

def render_posts():
    for post in Path(POSTS_DIR).glob('**/*.kcdoc'):
        content, frontmatter = kcdoc.to_html(post.read_text())
        if not { 'title', 'desc', 'date' } <= frontmatter.keys():
            error(f'misformed frontmatter in {post}.')

        frontmatter['date'] = isoparse(frontmatter['date']).strftime('%Y-%m-%d')
        post.with_suffix('.html').write_text(
            j2env.get_template(POST_TMPL).render(
                { 'post': { 'content': content, **frontmatter } }
            )
        )

def main():
    renderj2()
    render_posts()

if __name__ == '__main__':
    main()
