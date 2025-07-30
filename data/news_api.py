import flask
from flask import jsonify, make_response, request

from .db_session import session_manager
from .news import News
from .users import User

blueprint = flask.Blueprint(
    'news_api',
    __name__,
    template_folder='templates'
)


@blueprint.route('/api/news', methods=['GET'])
def get_news():
    with session_manager.create_session() as db_sess:
        news = db_sess.query(News).all()
        return jsonify(
            {
                'news': [
                    item.to_dict(only=('title', 'content', 'user.name'))
                    for item in news]
            }
        )


@blueprint.route('/api/news/<int:news_id>', methods=['GET'])
def get_one_news(news_id):
    with session_manager.create_session() as db_sess:
        news = db_sess.query(News).get(news_id)
        if not news:
            return make_response(jsonify({'error': 'Not found'}), 404)
        return jsonify(
            {
                'news': news.to_dict(only=('title', 'content', 'user_id', 'is_private'))
            }
        )


@blueprint.route('/api/news', methods=['POST'])
def create_news():
    if not request.json:
        return make_response(jsonify({'error': 'Empty request'}), 400)
    elif not all(key in request.json for key in
                 ['title', 'content', 'user_id', 'is_private']):
        return make_response(jsonify({'error': 'Bad request'}), 400)
    with session_manager.create_session() as db_sess:
        news = News(
            title=request.json['title'],
            content=request.json['content'],
            user_id=request.json['user_id'],
            is_private=request.json['is_private']
        )
        db_sess.add(news)
        db_sess.commit()
        return jsonify({'id': news.id})


@blueprint.route('/api/news/<int:news_id>', methods=['DELETE'])
def delete_news(news_id):
    with session_manager.create_session() as db_sess:
        news = db_sess.get(News, news_id)
        if not news:
            return make_response(jsonify({'error': 'Not found'}), 404)
        db_sess.delete(news)
        db_sess.commit()
        return jsonify({'success': 'OK'})


@blueprint.route('/api/news/<int:news_id>', methods=['PUT'])
def update_news(news_id):
    # Проверяем наличие JSON в запросе
    if not request.json:
        return make_response(jsonify({'error': 'Empty request'}), 400)

    # Получаем сессию базы данных
    with session_manager.create_session() as db_sess:

        # Ищем новость по ID
        news = db_sess.query(News).filter(News.id == news_id).first()

        # Если новость не найдена
        if not news:
            return make_response(jsonify({'error': 'News not found'}), 404)

        # Обновляем поля, если они переданы в запросе
        try:
            if 'title' in request.json:
                news.title = request.json['title']
            if 'content' in request.json:
                news.content = request.json['content']
            if 'user_id' in request.json:
                news.user_id = request.json['user_id']
            if 'is_private' in request.json:
                news.is_private = request.json['is_private']

            db_sess.commit()
            return jsonify({'success': True})

        except Exception as e:
            db_sess.rollback()
            return make_response(jsonify({'error': str(e)}), 500)


@blueprint.route('/api/user', methods=['POST'])
def register():
    try:
        data = request.get_json()

        if not data or not all(key in data for key in ('name', 'email', 'password', 'password_again', 'about')):
            return jsonify({'error': 'Неверные или отсутствующие параметры'}), 400

        name = data['name']
        email = data['email']
        password = data['password']
        password_again = data['password_again']
        about = data['about']

        if password != password_again:
            return jsonify({'error': 'Пароли не совпадают'}), 400

        # Работа с базой данных
        with session_manager.create_session() as db_sess:
            if db_sess.query(User).filter(User.email == email).first():
                return jsonify({'error': 'Пользователь с таким email уже существует'}), 409

            new_user = User(name=name, email=email, about=about)
            new_user.set_password(password)

            db_sess.add(new_user)
            db_sess.commit()

        return jsonify({'message': 'Регистрация успешна'}), 201

    except Exception as e:
        # Логируем и возвращаем ошибку
        return jsonify({'error': f'Ошибка сервера: {str(e)}'}), 500


@blueprint.route('/api/user/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Пустой запрос'}), 400

        with session_manager.create_session() as db_sess:
            user = db_sess.query(User).get(user_id)
            if not user:
                return jsonify({'error': 'Пользователь не найден'}), 404

            # Обновляем доступные поля (только если они переданы)
            for field in ('name', 'email', 'about'):
                if field in data:
                    setattr(user, field, data[field])

            if 'password' in data:
                user.set_password(data['password'])

            db_sess.commit()
            return jsonify({'message': 'Пользователь обновлён'}), 200

    except Exception as e:
        return jsonify({'error': f'Ошибка сервера: {str(e)}'}), 500


@blueprint.route('/api/user/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    try:
        with session_manager.create_session() as db_sess:
            user = db_sess.query(User).get(user_id)
            if not user:
                return jsonify({'error': 'Пользователь не найден'}), 404

            db_sess.delete(user)
            db_sess.commit()
            return jsonify({'message': 'Пользователь удалён'}), 200

    except Exception as e:
        return jsonify({'error': f'Ошибка сервера: {str(e)}'}), 500


@blueprint.route('/api/users', methods=['GET'])
def get_all_users():
    with session_manager.create_session() as db_sess:
        users = db_sess.query(User).all()
        return jsonify([
            {
                'id': user.id,
                'username': user.name,
                'email': user.email,
                'create_data': user.create_data.isoformat()
            }
            for user in users
        ])


@blueprint.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    with session_manager.create_session() as db_sess:
        user = db_sess.query(User).filter_by(id=user_id).first()
        if not user:
            return jsonify({'error': 'Пользователь не найден'}), 404

        return jsonify({
            'id': user.id,
            'username': user.name,
            'email': user.email,
            'create_data': user.create_data.isoformat(),
            'news': [
                {
                    'id': news.id,
                    'title': news.title,
                    'content': news.content,
                    'is_private': news.is_private
                }
                for news in user.news
            ]
        })
