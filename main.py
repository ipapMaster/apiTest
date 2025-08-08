from flask import Flask, render_template, redirect, make_response, jsonify, request, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from data import news_api
from data.db_session import session_manager
from data.news import News
from data.users import User
from forms.loginform import LoginForm
from forms.news import NewsForm
from forms.user import Register
from flasgger import Swagger

app = Flask(__name__)
swagger = Swagger(app)


login_manager = LoginManager()
login_manager.init_app(app)

app.config['SECRET_KEY'] = 'just_secret_key'


@login_manager.user_loader
def load_user(user_id):
    with session_manager.create_session() as db_sess:
        return db_sess.get(User, user_id)


@app.errorhandler(400)
def bad_request(_):
    return make_response(jsonify({'error': 'Некорректный запрос'}), 400)


@app.errorhandler(404)
def not_found(_):
    if request.path.startswith('/api'):
        return make_response(jsonify({'error': 'Не найдено'}), 404)
    else:
        return render_template('404.html', title='Не найдено'), 404


@app.errorhandler(401)
def not_authorized(error):
    if request.path.startswith('/api'):
        return make_response(jsonify({'error': 'Не авторизован'}), 401)
    return redirect('/login')


@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html', title='Наш сайт', current_page='')


@app.route('/about')
def about():
    return render_template('about.html', title='О сайте', current_page='about')


@app.route('/contacts')
def contacts():
    return render_template('contacts.html', title='Наши контакты', current_page='contacts')


@app.route('/news')
def all_news():
    with session_manager.create_session() as db_sess:
        news = db_sess.query(News).all()
        return render_template('news.html', title='Список новостей', current_page='news', news=news)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        with session_manager.create_session() as db_sess:
            user = db_sess.query(User).filter(User.email == form.email.data).first()
            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember_me.data)
                return redirect('/')
            return render_template('login.html',
                                   message='Неверный логин или пароль',
                                   title='Ошибка авторизации',
                                   form=form)
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')


@app.route('/register', methods=['POST', 'GET'])
def register():
    form = Register()
    if form.validate_on_submit():  # тоже самое, что и request.method == 'POST'
        # если пароли не совпали
        if form.password.data != form.password_again.data:
            return render_template('register.html',
                                   title='Регистрация',
                                   message='Пароли не совпадают',
                                   form=form)

        with session_manager.create_session() as db_sess:

            # Если пользователь с таким E-mail в базе уже есть
            if db_sess.query(User).filter(User.email == form.email.data).first():
                return render_template('register.html',
                                       title='Регистрация',
                                       message='Такой пользователь уже есть',
                                       form=form)
            user = User(
                name=form.name.data,
                email=form.email.data,
                about=form.about.data
            )
            user.set_password(form.password.data)
            db_sess.add(user)
            db_sess.commit()
            return redirect('/login')
    return render_template('register.html',
                           title='Регистрация', form=form)


@app.route('/newsjob', methods=['GET', 'POST'])
@login_required
def add_news():
    form = NewsForm()
    if form.validate_on_submit():
        with session_manager.create_session() as db_sess:
            news = News()
            news.title = form.title.data
            news.content = form.content.data
            news.is_private = form.is_private.data
            news.user_id = current_user.id  # Прямое связывание

            db_sess.add(news)
            db_sess.commit()
            return redirect('/news')
    return render_template('newsjob.html',
                           title='Добавление новости',
                           form=form)


@app.route('/newsdel/<int:news_id>')
@login_required
def news_delete(news_id):
    with session_manager.create_session() as db_sess:
        news = db_sess.query(News).filter(
            News.id == news_id, News.user == current_user
        ).first()

        if news:
            db_sess.delete(news)
            db_sess.commit()
        else:
            abort(404)
        return redirect('/news')


@app.route('/newsjob/<int:id_num>', methods=['GET', 'POST'])
@login_required
def edit_news(id_num):
    form = NewsForm()
    if request.method == 'GET':
        with session_manager.create_session() as db_sess:
            news = db_sess.query(News).filter(
                News.id == id_num, News.user == current_user
            ).first()
            if news:
                form.title.data = news.title
                form.content.data = news.content
                form.is_private.data = news.is_private
            else:
                abort(404)
    if form.validate_on_submit():
        with session_manager.create_session() as db_sess:
            news = db_sess.query(News).filter(
                News.id == id_num, News.user == current_user
            ).first()
            if news:
                news.title = form.title.data
                news.content = form.content.data
                news.is_private = form.is_private.data
                db_sess.commit()
                return redirect('/news')
            else:
                abort(404)
    return render_template('newsjob.html',
                           title='Редактирование новости',
                           form=form)


if __name__ == '__main__':
    session_manager.global_init('db/news.sqlite')
    app.register_blueprint(news_api.blueprint)  # подключаем blueprint API
    app.run(host='127.0.0.1', port=5000, debug=False)
