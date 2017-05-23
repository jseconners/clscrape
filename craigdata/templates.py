######################################################
#
# templates used by xpathtpl module for parsing
# craiglist pages
#
######################################################

# template for getting all craigslist pages from all
# countries and cities
sites_template = {
    'sites': {
        '_xpath': '//section[@class="body"]/h1',
        'country': {
            '_xpath': './text()'
        },
        'states': {
            '_xpath': './following-sibling::div[1]//h4',
            'name': {
                '_xpath': './text()'
            },
            'cities': {
                '_xpath': './following-sibling::ul[1]/li/a',
                'name': {
                    '_xpath': './text()'
                },
                'href': {
                    '_xpath': './@href'
                }
            }
        }
    }
}

# template for getting all sections
sections_template = {
    'sections': {
        '_xpath': '//h4[@class="ban"]',
        'name': {
            '_xpath': '.'
        },
        'href': {
            '_xpath': './a/@href'
        },
        'sub-sections': {
            '_xpath': './following-sibling::div[@class="cats"]/ul/li/a',
            'name': {
                '_xpath': '.'
            },
            'href': {
                '_xpath': './@href'
            }
        }
    }
}