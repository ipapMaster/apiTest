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
    """
    Получить список всех новостей
    ---
    tags:
      - News
    responses:
      200:
        description: Список новостей
        content:
          application/json:
            schema:
              type: object
              properties:
                news:
                  type: array
                  items:
                    type: object
                    properties:
                      title:
                        type: string
                      content:
                        type: string
                      user:
                        type: object
                        properties:
                          name:
                            type: string
    """
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
    """
    Получить новость по ID
    ---
    tags:
      - News
    parameters:
      - name: news_id
        in: path
        required: true
        schema:
          type: integer
    responses:
      200:
        description: Новость найдена
        content:
          application/json:
            schema:
              type: object
              properties:
                news:
                  type: object
                  properties:
                    title:
                      type: string
                    content:
                      type: string
                    user_id:
                      type: integer
                    is_private:
                      type: boolean
      404:
        description: Новость не найдена
    """
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
    """
    Создать новую новость
    ---
    tags:
      - News
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - title
              - content
              - user_id
              - is_private
            properties:
              title:
                type: string
              content:
                type: string
              user_id:
                type: integer
              is_private:
                type: boolean
    responses:
      200:
        description: Новость успешно создана
        content:
          application/json:
            schema:
              type: object
              properties:
                id:
                  type: integer
      400:
        description: Некорректный запрос
    """
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
    """
    Удалить новость по ID
    ---
    tags:
      - News
    parameters:
      - name: news_id
        in: path
        required: true
        schema:
          type: integer
    responses:
      200:
        description: Новость удалена
        content:
          application/json:
            schema:
              type: object
              properties:
                success:
                  type: string
      404:
        description: Новость не найдена
    """
    with session_manager.create_session() as db_sess:
        news = db_sess.get(News, news_id)
        if not news:
            return make_response(jsonify({'error': 'Not found'}), 404)
        db_sess.delete(news)
        db_sess.commit()
        return jsonify({'success': 'OK'})


@blueprint.route('/api/news/<int:news_id>', methods=['PUT'])
def update_news(news_id):
    """
    Обновить новость по ID
    ---
    tags:
      - News
    parameters:
      - name: news_id
        in: path
        required: true
        schema:
          type: integer
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              title:
                type: string
              content:
                type: string
              user_id:
                type: integer
              is_private:
                type: boolean
    responses:
      200:
        description: Новость обновлена
        content:
          application/json:
            schema:
              type: object
              properties:
                success:
                  type: boolean
      400:
        description: Некорректный запрос
      404:
        description: Новость не найдена
    """
    if not request.json:
        return make_response(jsonify({'error': 'Empty request'}), 400)

    with session_manager.create_session() as db_sess:
        news = db_sess.query(News).filter(News.id == news_id).first()
        if not news:
            return make_response(jsonify({'error': 'News not found'}), 404)

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
    """
    Регистрация пользователя
    ---
    tags:
      - User
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - name
              - email
              - password
              - password_again
              - about
            properties:
              name:
                type: string
              email:
                type: string
              password:
                type: string
              password_again:
                type: string
              about:
                type: string
    responses:
      201:
        description: Регистрация успешна
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
      400:
        description: Ошибка в параметрах
      409:
        description: Пользователь с таким email уже существует
    """
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

        with session_manager.create_session() as db_sess:
            if db_sess.query(User).filter(User.email == email).first():
                return jsonify({'error': 'Пользователь с таким email уже существует'}), 409

            new_user = User(name=name, email=email, about=about)
            new_user.set_password(password)

            db_sess.add(new_user)
            db_sess.commit()

        return jsonify({'message': 'Регистрация успешна'}), 201

    except Exception as e:
        return jsonify({'error': f'Ошибка сервера: {str(e)}'}), 500


@blueprint.route('/api/user/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """
    Обновить пользователя
    ---
    tags:
      - User
    parameters:
      - name: user_id
        in: path
        required: true
        schema:
          type: integer
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              name:
                type: string
              email:
                type: string
              about:
                type: string
              password:
                type: string
    responses:
      200:
        description: Пользователь обновлен
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
      400:
        description: Пустой запрос
      404:
        description: Пользователь не найден
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Пустой запрос'}), 400

        with session_manager.create_session() as db_sess:
            user = db_sess.query(User).get(user_id)
            if not user:
                return jsonify({'error': 'Пользователь не найден'}), 404

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
    """
    Удалить пользователя
    ---
    tags:
      - User
    parameters:
      - name: user_id
        in: path
        required: true
        schema:
          type: integer
    responses:
      200:
        description: Пользователь удален
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
      404:
        description: Пользователь не найден
    """
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
    """
    Получить всех пользователей
    ---
    tags:
      - User
    responses:
      200:
        description: Список пользователей
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  username:
                    type: string
                  email:
                    type: string
                  create_data:
                    type: string
    """
    with session_manager.create_session() as db_sess:
        users = db_sess.query(User).all()
        return jsonify(
            [
                user.to_dict(only=('id', 'username', 'email', 'create_data'))
                for user in users
            ]
        )


@blueprint.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """
    Получить пользователя по ID
    ---
    tags:
      - User
    parameters:
      - name: user_id
        in: path
        required: true
        schema:
          type: integer
    responses:
      200:
        description: Пользователь найден
        content:
          application/json:
            schema:
              type: object
              properties:
                id:
                  type: integer
                username:
                  type: string
                email:
                  type: string
                create_data:
                  type: string
                news:
                  type: array
                  items:
                    type: object
                    properties:
                      id:
                        type: integer
                      title:
                        type: string
                      content:
                        type: string
                      is_private:
                        type: boolean
      404:
        description: Пользователь не найден
    """
    with session_manager.create_session() as db_sess:
        user = db_sess.query(User).get(user_id)
        if not user:
            return make_response(jsonify({'error': 'Not found'}), 404)
        return jsonify(user.to_dict(
            only=('id', 'username', 'email', 'create_data'),
            rels={'news': ('id', 'title', 'content', 'is_private')}
        ))
