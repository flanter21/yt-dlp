from .common import InfoExtractor
import re, base64, urllib.parse, json
from ..utils.traversal import traverse_obj
from ..utils import (
    parse_iso8601,
    urlencode_postdata,
    mimetype2ext,
    smuggle_url,
    unsmuggle_url
)


'''APIs references - Blackboard Learn: https://developer.blackboard.com/portal/displayApi
                   - Blackboard Collaborate: https://github.com/blackboard/BBDN-Collab-Postman-REST'''

class BlackboardCollaborateIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                        https?://
                        (?P<region>[a-z]+)(?:-lti)?\.bbcollab\.com/
                        (?:
                            collab/ui/session/playback/load|
                            recording
                        )/
                        (?P<id>[^/\?]+)
                        \??(authToken=(?P<token>[\w\.\-]+))?'''
    _TESTS = [
        {
            'url': 'https://us-lti.bbcollab.com/collab/ui/session/playback/load/0a633b6a88824deb8c918f470b22b256',
            'md5': 'bb7a055682ee4f25fdb5838cdf014541',
            'info_dict': {
                'id': '0a633b6a88824deb8c918f470b22b256',
                'title': 'HESI A2 Information Session - Thursday, May 6, 2021 - recording_1',
                'ext': 'mp4',
                'duration': 1896,
                'timestamp': 1620333295,
                'upload_date': '20210506',
                'subtitles': {
                    'live_chat': 'mincount:1',
                },
            },
        },
        {
            'url': 'https://eu.bbcollab.com/collab/ui/session/playback/load/4bde2dee104f40289a10f8e554270600',
            'md5': '108db6a8f83dcb0c2a07793649581865',
            'info_dict': {
                'id': '4bde2dee104f40289a10f8e554270600',
                'title': 'Meeting - Azerbaycanca erize formasi',
                'ext': 'mp4',
                'duration': 880,
                'timestamp': 1671176868,
                'upload_date': '20221216',
            }
        },
        {
            'url': 'https://eu.bbcollab.com/recording/f83be390ecff46c0bf7dccb9dddcf5f6',
            'md5': 'e3b0b88ddf7847eae4b4c0e2d40b83a5',
            'info_dict': {
                'id': 'f83be390ecff46c0bf7dccb9dddcf5f6',
                'title': 'Keynote lecture by Laura Carvalho - recording_1',
                'ext': 'mp4',
                'duration': 5506,
                'timestamp': 1662721705,
                'upload_date': '20220909',
                'subtitles': {
                    'live_chat': 'mincount:1',
                },
            }
        },
        {
            'url': 'https://eu.bbcollab.com/recording/c3e1e7c9e83d4cd9981c93c74888d496',
            'md5': 'fdb2d8c43d66fbc0b0b74ef5e604eb1f',
            'info_dict': {
                'id': 'c3e1e7c9e83d4cd9981c93c74888d496',
                'title': 'International Ally User Group - recording_18',
                'ext': 'mp4',
                'duration': 3479,
                'timestamp': 1721919621,
                'upload_date': '20240725',
                'subtitles': {
                    'en': 'mincount:1',
                    'live_chat': 'mincount:1',
                },
            }
        },
        {
            'url': 'https://us.bbcollab.com/collab/ui/session/playback/load/76761522adfe4345a0dee6794bbcabda',
            'only_matching': True,
        },
        {
            'url': 'https://ca.bbcollab.com/collab/ui/session/playback/load/b6399dcb44df4f21b29ebe581e22479d',
            'only_matching': True,
        },
        {
            'url': 'https://eu.bbcollab.com/recording/51ed7b50810c4444a106e48cefb3e6b5',
            'only_matching': True,
        },
        {
            'url': 'https://au.bbcollab.com/collab/ui/session/playback/load/2bccf7165d7c419ab87afc1ec3f3bb15',
            'only_matching': True,
        },
    ]

    def _real_extract(self, url):
        # Prepare for requests
        mobj = self._match_valid_url(url)
        region = mobj.group('region')
        video_id = mobj.group('id')
        token = mobj.group('token')

        headers = {'Authorization': f'Bearer {token}'}
        base_url = f'https://{region}.bbcollab.com/collab/api/csa/recordings/{video_id}'

        # Try request the way the player handles it when behind a login
        if video_info := self._download_json(f'{base_url}/data/secure', video_id,
                                             'Using auth token (if available)',
                                             headers=headers, fatal=False):
            video_extra = self._download_json(f'{base_url}', video_id, 'Retrieving extra attributes', headers=headers, fatal=False)

        # Blackboard will allow redownloading from the same IP without authentication for a while, so if previous method fails, try this
        else:
            video_info = self._download_json(f'{base_url}/data', video_id, 'Trying fallback')
            video_extra = 0

        # Get metadata
        duration = video_info.get('duration')/1000
        title = video_info.get('name')
        upload_date = video_info.get('created')

        # Get streams
        stream_formats = []
        streams = video_info.get('extStreams') # Can also use video_info.get('streams') but I don't know its structure

        for current_stream in streams:
            stream_formats.append({
                'url': current_stream['streamUrl'],
                'container': mimetype2ext(current_stream.get('contentType')),
                'filesize': video_extra.get('storageSize', None),
                'aspect_ratio': video_info.get('aspectRatio', ''),
                })

        # Get subtitles
        subtitles = {}
        subs = video_info.get('subtitles')
        for current_subs in subs:
            lang_code = current_subs.get('lang')
            subtitles.setdefault(lang_code, []).append({
                'name': current_subs.get('label'),
                'url': current_subs['url']
                })

        # Get chat
        chats = video_info.get('chats')
        for current_chat in chats:
            subtitles.setdefault('live_chat', []).append({'url': current_chat['url']})

        return {
            'duration': duration,
            'formats': stream_formats,
            'id': video_id,
            'timestamp': parse_iso8601(upload_date),
            'subtitles': subtitles,
            'title': title,
        }

class BlackboardCollaborateLaunchIE(InfoExtractor):
    _VALID_URL = r'https?://[a-z]+(?:-lti)?\.bbcollab\.com/launch/(?P<token>[\w\.\-]+)'

    def _real_extract(self, url):
        token = self._match_valid_url(url)['token']
        video_id = traverse_obj(json.loads(base64.b64decode(token.split('.')[1] + "===")), ('resourceAccessTicket', 'resourceId'))

        redirect_url = self._request_webpage(url, video_id=video_id).url
        return self.url_result(redirect_url,
            ie=BlackboardCollaborateIE.ie_key(), video_id=video_id)

class BlackboardClassCollaborateIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                        https?://(?P<region>[a-z]+)(?:-lti)?\.bbcollab\.com/
                        (?:collab/ui/scheduler/)?
                        lti/?\??(token=(?P<token>[\w%\.\-]+))'''

    def _real_extract(self, url):
        url, data = unsmuggle_url(url, {})
        mobj = self._match_valid_url(url)
        region = mobj['region']
        token = urllib.parse.unquote(mobj['token'])
        token_info = json.loads(base64.b64decode(token.split('.')[1] + '==='))

        # Download playlist information
        endpoint = f'https://{region}.bbcollab.com/collab/api/csa/recordings'
        headers = {'Authorization': f'Bearer {token}'}
        playlist_info = self._download_json(endpoint, token_info['context'], 'Downloading playlist information', headers=headers)

        # Write playlist entries and send to BlackboardCollaborateIE
        entries = []
        for i in playlist_info['results']:
            current_url = self._download_json(f'{endpoint}/{i["id"]}/url', i['id'], 'Getting URL for each item', headers=headers)['url']

            # Is it public? Maybe this doesn't work
            if i['publicLinkAllowed'] == True:
                availability = 'public'
            else:
                availability = 'needs_auth'

            entries.append({
                'id': i['id'],
                '_type': 'url',
                'url': current_url,
                'view_count': i['playbackCount'],
                'duration': i['duration']/1000,
                'availability': availability,
                'ie_key': BlackboardCollaborateLaunchIE.ie_key(),
                })

        return self.playlist_result(
            entries,
            playlist_count=playlist_info['size'],
            title=data.get('title'),
            alt_title=data.get('alt_title'),
            description=data.get('description'),
            modified_timestamp=data.get('modified_timestamp'),
            channel_id=data.get('channel_id'))

class BlackboardCollaborateUltraSingleCourseIE(InfoExtractor):
    # Support format of either host/webapps/collab-ultra/tool/collabultra\?course_id=course_id or
    #                          host/webapps/blackboard/execute/courseMain\?course_id=course_id
    #                          host/ultra/courses/course_id/cl/outline
    _VALID_URL = r'''(?x)
                        https://(?P<host>[\w\.]+)/
                        ((webapps/
                                 (collab-ultra/tool/collabultra|blackboard/execute/courseMain)
                                 \?course_id=(?P<course_id>[\d_]+))
                        |(ultra/courses/(?P<course_id2>[\d_]+)/cl/outline))'''

    _TESTS = [ # All Require a login
        {
            'url': 'https://umb.umassonline.net/webapps/collab-ultra/tool/collabultra?course_id=_70544_1',
            'only_matching': True,
        },
        {
            'url': 'https://online.uwl.ac.uk/webapps/collab-ultra/tool/collabultra?course_id=_1445',
            'only_matching': True,
        },
        {
            'url': 'https://lms.mu.edu.sa/webapps/collab-ultra/tool/collabultra?course_id=_65252_1&mode=cpview',
            'only_matching': True,
        },
        {
            'url': 'https://nestor.rug.nl/webapps/collab-ultra/tool/collabultra?course_id=_404619_1',
            'only_matching': True,
        },
    ]
    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        course_id = mobj.group('course_id') or mobj.group('course_id2')
        host = mobj.group('host')

        course_data = self._download_webpage(
            f'https://{host}/webapps/collab-ultra/tool/collabultra/lti/launch?course_id={course_id}', course_id, 'Downloading course data')

        # Get attribute values from html. These will later be used as POST data for a request.
        attrs = dict(re.findall(r'<input[^>]+name="(?P<name>[^"]+)"[^>]+value="(?P<value>[^"]+)"', course_data))

        # Url to retrieve information about playlist from, endpoint
        endpoint = self._html_search_regex(r'<form[^>]+action="([^"]+)"', course_data, 'form_action')

        # Get authentication token
        redirect_url = self._request_webpage(endpoint, course_id, 'Getting authentication token', data=urlencode_postdata(attrs)).url

        course_info = self._download_json(
            f'https://{host}/learn/api/v1/courses/{course_id}', course_id, 'Downloading extra metadata', fatal=False)

        return self.url_result(smuggle_url(redirect_url, {
            'title': course_info.get('displayName'),
            'alt_title': course_info.get('displayId'), # Could also use courseId
            'description': course_info.get('description'),
            'modified_timestamp': parse_iso8601(course_info.get('modifiedDate')),
            'channel_id': course_id}),
            ie=BlackboardClassCollaborateIE.ie_key(), video_id=None)


class BlackboardCollaborateUltraAllCoursesIE(InfoExtractor):
    _VALID_URL = r'https://(?P<host>[\w\.]+)/ultra/institution-page'

    _TESTS = [ # All Require a login
        {
            'url': 'https://umb.umassonline.net/ultra/institution-page',
            'only_matching': True,
        },
        {
            'url': 'https://online.uwl.ac.uk/ultra/institution-page',
            'only_matching': True,
        },
        {
            'url': 'https://lms.mu.edu.sa/ultra/institution-page',
            'only_matching': True,
        },
        {
            'url': 'https://nestor.rug.nl/ultra/institution-page',
            'only_matching': True,
        },
    ]

    def _real_extract(self, url):
        host = self._match_valid_url(url)['host']
        endpoint = f'https://{host}/learn/api/v1/users/me/memberships?fields=course&includeCount=true'
        number_of_courses, courses_found, user_id, entries = 1, 0, None, []

        # Number of results per page seems to depend on the host and while it can be changed by '&limit=', each host seems to have a different upperbound, so a loop might be better
        while number_of_courses > courses_found:

            # Get page containing details about enrolled courses
            current_page = self._download_json(f"{endpoint}&offset={courses_found}", user_id,
                                               'Finding courses')
            number_of_courses = traverse_obj(current_page, ('paging', 'count'))
            user_id = traverse_obj(current_page, ('results', '0', 'userId'))
            courses_found += len(current_page['results'])

            # Process results to send to BlackboardCollaborateUltraSingleCourseIE
            for current_course in traverse_obj(current_page, ('results', ..., 'course')):
                if current_course['isAvailable']:
                    entries.append({
                        'id': current_course.get('id'),
                        'title': current_course.get('displayName'),
                        'alt_title': current_course.get('displayId'),
                        '_type': 'url',
                        'url': current_course.get('externalAccessUrl') or f"{host}/{current_course.get('homePageUrl')}",
                        'ie_key': BlackboardCollaborateUltraSingleCourseIE.ie_key(),
                        })

        return self.playlist_result(entries)