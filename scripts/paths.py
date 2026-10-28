"""Reject paths that could escape the extracted guest filesystem."""


def validate_paths(entries):
    links = {name: item['target'] for name, item in entries.items() if item['kind'] == 'link'}
    for name in entries:
        if not isinstance(name, str):
            raise ValueError('Pack paths must be strings.')
        parts = name.split('/')
        if len(name.encode('utf-8')) > 4096 or len(parts) > 64:
            raise ValueError('Pack path exceeds bounds.')
        if not name or '\\' in name or '\0' in name or any(part in ('', '.', '..') for part in parts):
            raise ValueError(f'Unsafe pack path: {name}')
        for end in range(1, len(parts)):
            parent = '/'.join(parts[:end])
            if parent in links:
                raise ValueError(f'Entry below a symbolic link: {name}')
            if parent in entries and entries[parent]['kind'] != 'directory':
                raise ValueError(f'Entry below a regular file: {name}')
    for name in links:
        resolve_link(name, links)


def resolve_link(name, links):
    target = links[name]
    if not isinstance(target, str) or len(target.encode('utf-8')) > 4096 or len(target.split('/')) > 65:
        raise ValueError('Link target exceeds bounds.')
    if not target or '\\' in target or '\0' in target:
        raise ValueError(f'Unsafe link target: {name}')
    pending = target.split('/')
    resolved = [] if target.startswith('/') else name.split('/')[:-1]
    followed = {name}
    while pending:
        part = pending.pop(0)
        if part in ('', '.'):
            continue
        if part == '..':
            if not resolved:
                raise ValueError(f'Link escapes guest root: {name}')
            resolved.pop()
            continue
        resolved.append(part)
        candidate = '/'.join(resolved)
        if candidate not in links:
            continue
        if candidate in followed:
            raise ValueError(f'Symbolic link cycle: {name}')
        if len(followed) >= 64:
            raise ValueError('Symbolic link chain exceeds bounds.')
        followed.add(candidate)
        nested = links[candidate]
        if not nested or '\\' in nested or '\0' in nested:
            raise ValueError(f'Unsafe link target: {candidate}')
        resolved = [] if nested.startswith('/') else resolved[:-1]
        pending = nested.split('/') + pending
