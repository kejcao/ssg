from pathlib import Path
from dateutil.parser import parse, ParserError
import sys
import pygments
import pygments.lexers
import pygments.formatters
import argparse
import jinja2
import jinja2.ext
import kcdoc

ROOTDIR = Path('/var/www/html/')
POSTS_DIR = ROOTDIR/'posts'
POST_TMPL = 'tmpls/post.j2'
IGNORE = list(Path(ROOTDIR/'tmpls').glob('**/*.j2'))

class Jinja2Highlight(jinja2.ext.Extension):
    tags = set(['highlight'])

    def __init__(self, env):
        super().__init__(env)

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        return jinja2.nodes.CallBlock(
            self.call_method('_highlight', [parser.parse_expression()]), [], [],
            parser.parse_statements(['name:endhighlight'], drop_needle=True)
        ).set_lineno(lineno)
    
    def _highlight(self, lang, caller):
        return pygments.highlight(
            jinja2.ext.Markup(caller().strip()).unescape(),
            pygments.lexers.get_lexer_by_name(lang),
            pygments.formatters.HtmlFormatter()
        )

j2env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(ROOTDIR),
    autoescape=jinja2.select_autoescape(),
    extensions=[Jinja2Highlight]
)

def error(msg):
    print('ssg:', msg, file=sys.stderr)
    sys.exit(1)

def should_update(src, dest):
    return (
        ARGS.all or not dest.exists() or
        src.stat().st_mtime > dest.stat().st_mtime
    )

def render_template(tmpl, data):
    try:
        return j2env.get_template(tmpl).render(data)
    except Exception as e:
        error(f'{tmpl}: {e}.')

def renderj2(posts):
    for src in Path(ROOTDIR).glob('**/*.j2'):
        dest = src.with_suffix('.html')
        if src not in IGNORE:
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

    return sorted(posts, key=lambda p: p['date'], reverse=True)

def main():
    global ARGS
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-a', '--all', action='store_true',
        help='render everything, regardless of modification time.'
    )
    ARGS = parser.parse_args()

    posts = render_posts()
    renderj2(posts)

if __name__ == '__main__':
    main()
