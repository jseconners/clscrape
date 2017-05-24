######################################################
#
# templates used by xpathtpl module for parsing
# craiglist pages
#
######################################################

# template for getting all craigslist pages from all
# countries and cities
pages_tpl = {
    'level': {
        '_xpath': '//section[@class="body"]/h1',
        '_ukeys': True,
        'level': {
            '_xpath': './following-sibling::div[1]//h4',
            '_ukeys': True,
            'level': {
                '_xpath': './following-sibling::ul[1]/li/a',
                '_ukeys': True,
                'href': {
                    '_xpath': './@href'
                }
            }
        }
    }
}

# template for getting all sections
sections_tpl = {
    'level': {
        '_xpath': '//h4[@class="ban"]',
        '_ukeys': True,
        'href': {
            '_xpath': './a/@href'
        },
        'level': {
            '_xpath': './following-sibling::div[@class="cats"]/ul/li/a',
            '_ukeys': True,
            'href': {
                '_xpath': './@href'
            }
        }
    }
}

submenu_tpl_a = {
    'level': {
        '_xpath': '//div[@class="leftside"]/h3',
        '_ukeys': True,
        'level': {
            '_xpath': './following-sibling::ul[1]/li/a',
            '_ukeys': True,
            'href': {
                '_xpath': './@href'
            }
        }
    }
}

submenu_tpl_b = {
    'level': {
        '_xpath': '//div[@class="links"]//a',
        '_ukeys': True,
        'href': {
            '_xpath': './@href'
        }
    }
}
