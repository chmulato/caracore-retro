(function () {
    const feature = document.getElementById('featured-article');
    const items = Array.from(document.querySelectorAll('.article-item'));
    const categoryRules = [
        {
            name: 'PDV',
            expression: /\bpdv\b|ponto de venda|varejo|terminal de venda|checkout|caixa/
        },
        {
            name: 'Identidade Digital',
            expression: /identidade|oidc|oauth|pkce|autentic|credencial|seguran/
        },
        {
            name: 'Mineração e ETE',
            expression: /miner|ete\b|hidrometalurg|processo quimic|saneamento|terras raras/
        },
        {
            name: 'Circuito',
            expression: /circuito|educa|aprendiz|aluno|escola|formacao/
        },
        {
            name: 'Roadmap',
            expression: /roadmap|hub|logistic|estrateg|finops|planejamento|portfolio/
        }
    ];

    if (!feature || items.length === 0) {
        throw new Error('A seção editorial precisa de um artigo em destaque e ao menos um artigo no arquivo.');
    }

    const normalize = (value) => (value || '')
        .toLocaleLowerCase('pt-BR')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '');

    function getCategory(item) {
        const topics = normalize(item.dataset.tags);
        const rule = categoryRules.find((candidate) => candidate.expression.test(topics));
        return rule ? rule.name : 'Tecnologia';
    }

    function createTextElement(tag, className, text) {
        const element = document.createElement(tag);
        element.className = className;
        element.textContent = text;
        return element;
    }

    function decorate(item, isFeatured) {
        const titleLink = item.querySelector('.article-title');
        if (!titleLink) {
            throw new Error('Um artigo do índice está sem título.');
        }

        const summary = item.dataset.summary;
        const articleDate = titleLink.href.match(/\/(\d{4})_(\d{2})_(\d{2})_article_/);

        if (!summary || !articleDate) {
            throw new Error('Um artigo do índice está sem título, resumo ou data válida.');
        }

        const title = titleLink.textContent.trim();
        const category = getCategory(item);
        const imageName = titleLink.getAttribute('href')
            .replace(/^articles\//, 'articles/assets/img/')
            .replace(/\.html$/, '_01.png');
        const cover = document.createElement('a');
        const picture = document.createElement('picture');
        const image = document.createElement('img');
        const content = document.createElement('div');
        const categoryLabel = createTextElement('span', 'editorial-category', category);
        const excerpt = createTextElement('p', 'editorial-excerpt', summary);
        const meta = document.createElement('div');
        const date = document.createElement('time');

        cover.className = 'editorial-cover';
        cover.href = titleLink.getAttribute('href');
        cover.setAttribute('aria-label', `Ler artigo: ${title}`);
        const mobileSource = document.createElement('source');
        const desktopSource = document.createElement('source');
        mobileSource.type = 'image/webp';
        mobileSource.media = '(max-width: 680px)';
        mobileSource.srcset = imageName.replace('_01.png', '_01_720.webp');
        desktopSource.type = 'image/webp';
        desktopSource.srcset = imageName.replace('_01.png', '_01_1600.webp');
        picture.append(mobileSource, desktopSource);
        image.src = imageName;
        image.alt = '';
        image.loading = isFeatured ? 'eager' : 'lazy';
        image.decoding = 'async';
        if (isFeatured) {
            image.fetchPriority = 'high';
        }
        picture.appendChild(image);
        cover.appendChild(picture);

        content.className = 'editorial-card-content';
        titleLink.textContent = title;
        content.append(categoryLabel, titleLink, excerpt);

        date.className = 'article-date';
        date.dateTime = `${articleDate[1]}-${articleDate[2]}-${articleDate[3]}`;
        date.textContent = new Intl.DateTimeFormat('pt-BR', {
            day: 'numeric',
            month: 'long',
            year: 'numeric',
            timeZone: 'UTC'
        }).format(new Date(`${date.dateTime}T12:00:00Z`));
        meta.className = 'editorial-card-meta';
        meta.appendChild(date);

        if (isFeatured) {
            const readLink = document.createElement('a');
            readLink.className = 'editorial-read-link';
            readLink.href = titleLink.getAttribute('href');
            readLink.textContent = 'Ler artigo';
            meta.appendChild(readLink);
        }

        content.appendChild(meta);
        item.dataset.editorialCategory = category;
        item.classList.toggle('article-item-featured', isFeatured);
        item.replaceChildren(cover, content);
    }

    items.forEach((item, index) => decorate(item, index === 0));
    feature.appendChild(items[0]);

    document.querySelectorAll('.month-group').forEach((month) => {
        if (!month.querySelector('.article-item')) {
            month.classList.add('is-hidden');
        }
    });
    document.querySelectorAll('.year-group').forEach((year) => {
        if (!year.querySelector('.month-group:not(.is-hidden)')) {
            year.classList.add('is-hidden');
        }
    });

    document.querySelectorAll('[data-category-filter]').forEach((button) => {
        button.addEventListener('click', () => {
            const input = document.getElementById('searchInput');
            const filters = document.getElementById('filters');
            const alreadySelected = button.getAttribute('aria-pressed') === 'true';
            document.querySelectorAll('[data-category-filter]').forEach((categoryButton) => {
                categoryButton.setAttribute('aria-pressed', 'false');
            });
            if (alreadySelected) {
                delete filters.dataset.categoryFilter;
            } else {
                filters.dataset.categoryFilter = button.dataset.categoryFilter;
                button.setAttribute('aria-pressed', 'true');
            }
            input.value = '';
            input.dispatchEvent(new Event('input', { bubbles: true }));
            filters.open = true;
            filters.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    });
}());
