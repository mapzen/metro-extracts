from flask import Blueprint, url_for

blueprint = Blueprint('ODES', __name__, template_folder='templates/odes')

def apply_odes_blueprint(app):
    '''
    '''
    app.register_blueprint(blueprint)

@blueprint.route('/odes')
def get_odes():
    '''
    '''
    return '''
        <form action="{href}" method="post">
            Sudo Make Me A New Extract<br>
            <label><input   value="37.81230" name="bbox_n"> North</label><br>
            <label><input value="-122.26447" name="bbox_w"> West</label><br>
            <label><input   value="37.79724" name="bbox_s"> South</label><br>
            <label><input value="-122.24825" name="bbox_e"> East</label><br>
            <input type="submit">
        </form>
        '''.format(href=url_for('.post_extract'))

@blueprint.route('/odes/extracts', methods=['POST'])
def post_extract():
    '''
    '''
    return 'We will get right on that.'
