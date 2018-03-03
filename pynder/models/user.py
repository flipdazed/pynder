import datetime

import dateutil.parser
import six

from pynder.constants import GENDER_MAP, SIMPLE_FIELDS
from pynder.models.message import Message
from pynder.errors import RequestError

class User(object):

    def __init__(self, data, session):
        self._session = session
        self._data = data
        self.id = data['_id']

        for field in SIMPLE_FIELDS:
            setattr(self, field, data.get(field))

        self.photos_obj = [photo for photo in data['photos']]
        self.birth_date = dateutil.parser.parse(self.birth_date)
        self.schools = []
        self.schools_id = []
        self.jobs = []
        try:
            self.schools.extend([school["name"] for school in data['schools']])
            self.schools_id.extend([school["id"] for school in data['schools']])
            self.jobs.extend(["%s @ %s" % (job["title"]["name"], job["company"][
                             "name"]) for job in data['jobs'] if 'title' in job and 'company' in job])
            self.jobs.extend(["%s" % (job["company"]["name"],) for job in data[
                             'jobs'] if 'title' not in job and 'company' in job])
            self.jobs.extend(["%s" % (job["title"]["name"],) for job in data[
                             'jobs'] if 'title' in job and 'company' not in job])
        except ValueError:
            pass
        except KeyError:
            pass

    @property
    def instagram_username(self):
        if self._data.get("instagram", False):
            return self._data['instagram']['username']

    @property
    def instagram_photos(self):
        if self._data.get("instagram", False):
            return [p for p in self._data['instagram']['photos']]

    @property
    def gender(self):
        return GENDER_MAP[int(self._data['gender'])]

    @property
    def common_likes(self):
        return [p for p in self._data['common_likes']]

    @property
    def common_connections(self):
        return [p for p in self._data['common_friends']]

    @property
    def thumbnails(self):
        return self.get_photos(width="84")

    @property
    def photos(self):
        return self.get_photos()

    @property
    def distance_km(self):
        if self._data.get("distance_mi", False) or self._data.get("distance_km", False):
            return self._data.get('distance_km', self._data['distance_mi'] * 1.60934)
        else:
            return 0

    @property
    def age(self):
        today = datetime.date.today()
        return (today.year - self.birth_date.year -
                ((today.month, today.day) <
                 (self.birth_date.month, self.birth_date.day)))

    def __unicode__(self):
        return u"{n} ({a})".format(n=self.name, a=self.age)

    def __str__(self):
        return six.text_type(self).encode('utf-8')

    def __repr__(self):
        return repr(self.name)

    def report(self, cause):
        return self._session._api.report(self.id, cause)

    def get_photos(self, width=None):
        photos_list = []
        for photo in self.photos_obj:
            if width is None:
                photos_list.append(photo.get("url"))
            else:
                sizes = ["84", "172", "320", "640"]
                if width not in sizes:
                    print("Only support these widths: %s" % sizes)
                    return None
                for p in photo.get("processedFiles", []):
                    if p.get("width", 0) == int(width):
                        photos_list.append(p.get("url", None))
        return photos_list


class Hopeful(User):

    def like(self):
        return self._session._api.like(self.id)['match']

    def superlike(self):
        return self._session._api.superlike(self.id)['match']

    def dislike(self):
        return self._session._api.dislike(self.id)


class Match(object):

    def __init__(self, match, _session, get_user=False):
        self._session = _session
        self.match = match
        self.id = match["_id"]
        self.user, self.user_id, self.messages = None, None, []
        self.deleted = False
        if 'person' in match:
            try:
                self.last_activity_date = dateutil.parser.parse(self.match['last_activity_date'])
                self.name = self.match['person']['name']
                self.user_id = self.match['person']['_id']
                if get_user:
                    self.refresh_user(_session)
                self.messages = [
                    Message(m, user=self.user)
                    for m in self.match['messages']
                ]
            except RequestError as e:
                print 'User Deleted: {}'.format(self.id)

    def refresh_messages(self, _session):
        if not self.id:
            return False
        self.message_data = _session._api.messages(self.id)
        if self.message_data is None:
            self.deleted = True
            return None
        self.message_data = self.message_data['data']
        self.messages = [
            Message(m, user=self.user)
            for m in self.message_data['messages']
        ]
        return self.messages

    def refresh_user(self, _session):
        if not self.user_id:
            return False
        self.user_data = _session._api.user_info(self.user_id)
        if self.user_data is None:
            self.deleted = True
            return None
        self.user_data = self.user_data['results']
        self.user_data['_id'] = self.user_id
        self.user = User(self.user_data, _session)
        return self.user

    def message(self, body):
        return self._session._api.message(self.id, body)['_id']

    def delete(self):
        return self._session._api._delete('/user/matches/' + self.id)

    def __repr__(self):
        if self.name is None:
            return "<Unnamed match>"
        elif self.user is None:
            return "{}".format(six.text_type(self.name).encode('utf-8'))
        else:
            return "{}, {:3.1f}km".format(six.text_type(self.user).encode('utf-8'), self.user.distance_km)
