import markdown
import re

def clean_status(status):
    clean = clean_dict(status, ['id', 'content', 'created_at', 'url', 'media_attachments', 'card'])
    clean['account'] = clean_author(status['account'])
    clean['content'] = markdown.markdown("<section markdown='block'>"+ clean['content'] +"</section>", extensions=['md_in_html'])
    for emoji in status['emojis']:
        clean['content'] = clean['content'].replace(":" + emoji['shortcode'] + ":", '<img alt="' + emoji['shortcode'] + ' emoji" class="emoji" src="'+emoji['url']+'" />')
    return clean

def clean_dict(dict, keys):
    return {k: dict[k] for k in keys}

def clean_html(raw_html):
    cleaner = re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')
    return re.sub(cleaner, '', raw_html)

def clean_author(account):
    if 'emojis' in account and len(account['emojis']) > 0:
        name = account['display_name']
        for emoji in account['emojis']:
            account['display_name'] = name.replace(":" + emoji['shortcode'] + ":", '<img alt="' + emoji['shortcode'] + ' emoji" class="emoji" src="'+emoji['url']+'" />')

    return clean_dict(account, ['avatar', 'display_name', 'id', 'url'])
