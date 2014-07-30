"""
Module to parse input and select form input.
Returns a dictionary of default values.
"""

def getFormDefaults(form):
    """Expects form is already a BeautifulSoup tag"""
    d = dict()
    inputs = form.find_all('input')
    for i in inputs:
        t = i.get('type')
        if t.lower() == 'text':
            d[i.get('name')] = i.get('value')
        elif t.lower() == 'checkbox':
            checked = i.get('checked')
            if checked != '':
                d[i.get('name')] = i.get('value')

    selects = form.find_all('select')
    for s in selects:
        name = s.get('name')
        opts = s.find_all('option')
        for o in opts:
            selected = o.get('selected')
            if selected != '':
                d[name] = o.value
                break

    return d
