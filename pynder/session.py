from time import time
from cached_property import cached_property

import pynder.api as api
from pynder.errors import InitializationError
from pynder.models import Profile, Hopeful, Match, Friend


class Session(object):

    def __init__(self, facebook_token=None, XAuthToken=None, proxies=None, facebook_id=None):
        if facebook_token is None and XAuthToken is None:
            raise InitializationError("Either XAuth or facebook token must be set")

        self._api = api.TinderAPI(XAuthToken, proxies)
        # perform authentication
        if XAuthToken is None:
            self._api.auth(facebook_id, facebook_token)

    @cached_property
    def profile(self):
        return Profile(self._api.profile(), self._api)

    def nearby_users(self, limit=10):
        while True:
            self.response = self._api.recs(limit)
            users = self.response['results'] if 'results' in self.response else []
            for user in users:
                if not user["_id"].startswith("tinder_rate_limited_id_"):
                    yield Hopeful(user, self)
            if not len(users):
                break

    def update_profile(self, profile):
        return self._api.update_profile(profile)

    def update_location(self, latitude, longitude):
        return self._api.ping(latitude, longitude)

    def matches(self, since=None):
        self.response = self._api.matches(since)
        return (Match(match, self) for match in self.response if 'person' in match)

    def get_fb_friends(self):
        """
        Returns array of all friends using Tinder Social.
        :return: Array of friends.
        :rtype: Friend[]
        """
        self.response = self._api.fb_friends()
        return (Friend(friend, self) for friend in self.response['results'])

    def updates(self, since=None):
        self.response = self._api.updates(since)
        return (Match(match, self) for match in self.response["matches"] if 'person' in match)

    @property
    def likes_remaining(self):
        return self._api.meta()['rating']['likes_remaining']

    @property
    def can_like_in(self):
        """
        Return the number of seconds before being allowed to issue likes
        """
        now = int(time())
        limited_until = self._api.meta()['rating'].get('rate_limited_until', now)
        return limited_until / 1000 - now

    @property
    def banned(self):
        return self.profile.banned
