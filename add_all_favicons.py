import os
import re

print("Adding favicon link to all HTML files...")

for root, dirs, files in os.walk('docs'):
    for file in files:
        if file.endswith('.html'):
            fpath = os.path.join(root, file)
            
            # Determine relative path to logo.png
            # Root is docs/
            # If root == docs, path to logo is assets/img/logo.png
            # If root == docs/articles, path to logo is assets/img/logo.png (since articles has its own assets)
            # If root == docs/articles/others, path to logo is ../assets/img/logo.png (goes up to articles)
            # If root == docs/regis, path to logo is ../assets/img/logo.png (goes up to docs)
            # If root == docs/facebook, path to logo is ../assets/img/logo.png (goes up to docs)
            
            rel_depth = os.path.relpath('docs', root)
            # rel_depth will be '.' for docs/
            # For docs/articles, rel_depth will be '..' but we want to point to articles/assets/img/logo.png or docs/assets/img/logo.png
            # Let's write a robust logic based on existence of assets folder
            
            # Let's check where the nearest 'assets/img/logo.png' is
            # 1. Check if ./assets/img/logo.png exists
            # 2. Check if ../assets/img/logo.png exists
            # 3. Check if ../../assets/img/logo.png exists
            
            logo_rel_path = None
            for depth in ['', '..', '../..', '../../..']:
                test_path = os.path.join(root, depth, 'assets/img/logo.png')
                if os.path.exists(os.path.normpath(test_path)):
                    logo_rel_path = os.path.join(depth, 'assets/img/logo.png').replace('\\', '/')
                    # Clean up './assets' to 'assets'
                    if logo_rel_path.startswith('/'):
                        logo_rel_path = logo_rel_path[1:]
                    if logo_rel_path.startswith('./'):
                        logo_rel_path = logo_rel_path[2:]
                    break
            
            if not logo_rel_path:
                # Fallback to root assets
                logo_rel_path = os.path.relpath('docs/assets/img/logo.png', root).replace('\\', '/')
                
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            # Check if favicon link is already there
            if 'rel="icon"' in content or 'rel="shortcut icon"' in content:
                # Let's replace the existing link to ensure it is correct
                content = re.sub(r'<link rel="(icon|shortcut icon)"[^>]*>', '', content)
                content = re.sub(r'<link href="[^"]*favicon\.ico"[^>]*>', '', content)
            
            # Inject favicon link
            favicon_tag = f'    <link rel="icon" type="image/png" href="{logo_rel_path}">'
            # Insert after <head>
            new_content = content.replace('<head>', f'<head>\n{favicon_tag}', 1)
            
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"  Added favicon {logo_rel_path} to {fpath}")

print("Done.")
