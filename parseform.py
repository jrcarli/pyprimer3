"""Helper to extract default values from an HTML form."""

__author__ = "Joe Carli"
__copyright__ = "Copyright 2014"
__credits__ = ["Joe Carli"]
__license__ = "GPL"
__version__ = "0.0.1"
__maintainer__ = "Joe Carli"
__email__ = "jrcarli@gmail.com"
__status__ = "Development"

def getFormDefaults(form):
    """Return a form's input field names and default values as a dictionary.

    Input (form) must be a BeautifulSoup tag.
    """
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
