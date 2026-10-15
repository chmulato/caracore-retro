import os
import re
from html.parser import HTMLParser
import urllib.parse

class BlogHTMLParser(HTMLParser):
    def __init__(self, filepath):
        super().__init__()
        self.filepath = filepath
        self.errors = []
        self.h1_count = 0
        self.main_count = 0
        self.has_meta_desc = False
        self.has_canonical = False
        self.has_noindex = False
        self.has_meta_refresh = False
        
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        
        if tag == 'h1':
            self.h1_count += 1

        if tag == 'main':
            self.main_count += 1
            
        if tag == 'meta' and attrs_dict.get('name') == 'description':
            if attrs_dict.get('content'):
                self.has_meta_desc = True

        if tag == 'meta' and attrs_dict.get('name', '').lower() == 'robots':
            self.has_noindex = 'noindex' in attrs_dict.get('content', '').lower()

        if tag == 'meta' and attrs_dict.get('http-equiv', '').lower() == 'refresh':
            self.has_meta_refresh = True
                
        if tag == 'link' and attrs_dict.get('rel') == 'canonical':
            if attrs_dict.get('href'):
                self.has_canonical = True

        ref_attrs = {
            'link': 'href',
            'script': 'src',
            'img': 'src',
            'a': 'href'
        }
        
        if tag in ref_attrs:
            attr_name = ref_attrs[tag]
            val = attrs_dict.get(attr_name)
            if val:
                # For <link> tags, only check if it is a stylesheet or icon/font preload
                if tag == 'link':
                    rel = attrs_dict.get('rel', '').lower()
                    if rel not in ['stylesheet', 'icon', 'shortcut icon', 'apple-touch-icon', 'preload']:
                        return # Ignore canonical, alternate RSS feed, etc.
                self.check_reference(tag, attr_name, val)
                
    def check_reference(self, tag, attr, val):
        if val.startswith(('mailto:', 'javascript:', '#')):
            return
            
        parsed = urllib.parse.urlparse(val)
        is_asset = tag in ['link', 'script', 'img'] or (tag == 'a' and val.lower().endswith(('.ttf', '.woff', '.woff2', '.png', '.jpg', '.jpeg', '.svg')))
        
        if parsed.netloc:
            if is_asset:
                self.errors.append(f"EXTERNAL ASSET FOUND: <{tag} {attr}=\"{val}\"> should be local.")
            return

        if parsed.scheme in ['http', 'https']:
            if is_asset:
                self.errors.append(f"EXTERNAL ASSET FOUND: <{tag} {attr}=\"{val}\"> should be local.")
            return
            
        if parsed.scheme == 'file' or val.startswith('file://'):
            self.errors.append(f"ABSOLUTE FILE:// PATH FOUND: <{tag} {attr}=\"{val}\"> must be relative.")
            return
            
        if parsed.path.startswith('/'):
            docs_root = os.path.abspath('docs')
            clean_path = parsed.path.lstrip('/')
            target_path = os.path.abspath(os.path.join(docs_root, clean_path))
            if os.path.commonpath([docs_root, target_path]) != docs_root:
                self.errors.append(f"ROOT-RELATIVE PATH ESCAPES DOCS: <{tag} {attr}=\"{val}\">")
                return
        elif os.path.isabs(val):
            self.errors.append(f"ABSOLUTE PATH FOUND: <{tag} {attr}=\"{val}\"> must be relative.")
            return
        else:
            file_dir = os.path.dirname(self.filepath)
            target_path = os.path.abspath(os.path.join(file_dir, parsed.path))
        
        if tag == 'a' and not val.endswith(('.html', '.png', '.jpg', '.css', '.js', '.ttf')):
            if not os.path.exists(target_path) and (val.startswith('www.') or '.' in val):
                return

        if not os.path.exists(target_path):
            self.errors.append(f"BROKEN LINK/FILE NOT FOUND: <{tag} {attr}=\"{val}\"> (Resolved: {target_path})")


def test_html_files():
    html_files = []
    for root, dirs, files in os.walk('docs'):
        if 'regis' in root:
            continue
        for file in files:
            if file.endswith('.html'):
                html_files.append(os.path.join(root, file))
                
    all_passed = True
    print("=== TESTING HTML FILES ===")
    
    for fpath in html_files:
        file_errors = []
        
        # 1. Check file encoding and DOCTYPE on line 1
        with open(fpath, 'rb') as f:
            raw_start = f.read(15)
        
        if raw_start.startswith(b'\xef\xbb\xbf'):
            file_errors.append("File starts with UTF-8 BOM character.")
        elif not raw_start.lower().startswith(b'<!doctype html>'):
            file_errors.append(f"File does not start with <!DOCTYPE html> cleanly. Found: {raw_start}")
            
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            html_content = f.read()
            
        parser = BlogHTMLParser(fpath)
        try:
            parser.feed(html_content)
        except Exception as e:
            file_errors.append(f"HTML Parser crashed: {e}")
            
        if parser.errors:
            file_errors.extend(parser.errors)
            
        if parser.h1_count == 0 and not parser.has_meta_refresh:
            print(f"  [WARN] {fpath} - SEO: Missing <h1> heading tag.")
        elif parser.h1_count > 1:
            file_errors.append(f"SEO: Found multiple <h1> tags ({parser.h1_count}). Only one <h1> is allowed.")
            
        if not parser.has_meta_desc and not parser.has_meta_refresh:
            print(f"  [WARN] {fpath} - SEO: Missing <meta name=\"description\"> tag.")
            
        if not parser.has_canonical and not parser.has_noindex:
            print(f"  [WARN] {fpath} - SEO: Missing <link rel=\"canonical\"> tag.")

        if parser.has_meta_refresh and not parser.has_canonical:
            file_errors.append("SEO: Redirect page must declare its canonical destination.")
            
        if file_errors:
            print(f"🔴 {fpath} - FAILED:")
            for err in file_errors:
                print(f"   - {err}")
            all_passed = False
        else:
            print(f"🟢 {fpath} - PASSED")
            
    return all_passed


def test_css_files():
    css_files = []
    for root, dirs, files in os.walk('docs'):
        if 'regis' in root:
            continue
        for file in files:
            if file.endswith('.css'):
                css_files.append(os.path.join(root, file))
                
    all_passed = True
    print("\n=== TESTING CSS FILES ===")
    
    for fpath in css_files:
        file_errors = []
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        imports = re.findall(r'@import\s+url\([\"\'\s]?(https?://[^\"\'\)]+)[\"\'\s]?\)', content)
        if imports:
            for imp in imports:
                file_errors.append(f"External @import found: {imp}")
            
        urls = re.findall(r'url\([\"\'\s]?([^\"\'\)]+)[\"\'\s]?\)', content)
        for url in urls:
            if url.startswith(('http://', 'https://')):
                file_errors.append(f"External CSS resource URL found: {url}")
                continue
            if url.startswith('data:'):
                continue
                
            file_dir = os.path.dirname(fpath)
            clean_path = url.split('?')[0].split('#')[0]
            target_path = os.path.abspath(os.path.join(file_dir, clean_path))
            
            if not os.path.exists(target_path):
                file_errors.append(f"CSS BROKEN RESOURCE: url(\"{url}\") not found. (Resolved: {target_path})")
                
        if file_errors:
            print(f"🔴 {fpath} - FAILED:")
            for err in file_errors:
                print(f"   - {err}")
            all_passed = False
        else:
            print(f"🟢 {fpath} - PASSED")
            
    return all_passed


def test_responsive_article_images():
    all_passed = True
    image_directory = os.path.join('docs', 'articles', 'assets', 'img')
    article_files = [
        path for path in os.listdir('docs/articles')
        if re.fullmatch(r'20\d{2}_\d{2}_\d{2}_article_\d+\.html', path)
    ]
    print("\n=== TESTING RESPONSIVE ARTICLE IMAGES ===")

    for filename in article_files:
        filepath = os.path.join('docs', 'articles', filename)
        with open(filepath, 'r', encoding='utf-8') as article:
            content = article.read()

        expected_images = set(re.findall(
            r'<img\b[^>]*\bsrc=["\']assets/img/(\d{4}_\d{2}_\d{2}_article_\d+_\d+\.png)["\']',
            content,
            re.IGNORECASE,
        ))
        responsive_pictures = {}
        for picture in re.finditer(
            r'<picture\b[^>]*>(.*?)</picture>',
            content,
            re.IGNORECASE | re.DOTALL,
        ):
            picture_content = picture.group(1)
            fallback = re.search(
                r'<img\b[^>]*\bsrc=["\']assets/img/(\d{4}_\d{2}_\d{2}_article_\d+_\d+\.png)["\']',
                picture_content,
                re.IGNORECASE,
            )
            if fallback:
                responsive_pictures[fallback.group(1)] = re.findall(
                    r'<source\b[^>]*\bsrcset=["\']([^"\']+)["\'][^>]*>',
                    picture_content,
                    re.IGNORECASE,
                )

        all_valid = True
        for image in expected_images:
            basename = os.path.splitext(image)[0]
            sources = responsive_pictures.get(image, [])
            expected_sources = (f"{basename}_720.webp", f"{basename}_1600.webp")
            if tuple(os.path.basename(source) for source in sources) != expected_sources:
                print(f"🔴 {filepath} - FAILED: {image} is missing responsive WebP sources.")
                all_passed = all_valid = False
                continue

            missing = [
                source for source in sources
                if not os.path.exists(os.path.join(os.path.dirname(filepath), source))
            ]
            if missing:
                print(f"🔴 {filepath} - FAILED: missing responsive assets: {', '.join(missing)}")
                all_passed = all_valid = False

        if all_valid:
            print(f"🟢 {filepath} - PASSED ({len(expected_images)} article images)")

    return all_passed


if __name__ == '__main__':
    html_ok = test_html_files()
    css_ok = test_css_files()
    responsive_images_ok = test_responsive_article_images()
    
    print("\n=== TEST SUMMARY ===")
    if html_ok and css_ok and responsive_images_ok:
        print("🟢 ALL ACTIVE BLOG FILES PASSED! The blog is 100% healthy, sovereign, and offline-compatible.")
        exit(0)
    else:
        print("🔴 ACTIVE BLOG TESTS FAILED! Review the errors above.")
        exit(1)
