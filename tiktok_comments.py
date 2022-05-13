import requests
from requests import get
import pprint
import logging
import functools
import typing


logger = logging.getLogger(__name__)


HEADERS = {
    "referer": "https://www.tiktok.com/@shammiltd/video/7095589308094024962?is_copy_url=1&is_from_webapp=v1",  # noqa: E501
    "sec-ch-ua": '" Not A;Brand";v="99", "Chromium";v="101", "Google Chrome";v="101"',  # noqa: E501
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36",  # noqa: E501
}


class RepeatHttp500Errors(object):
    def __init__(self, number_of_times_to_repeat: int) -> None:
        self.number_of_times_to_repeat: int = number_of_times_to_repeat

    def __call__(self, fn):
        @functools.wraps(fn)
        def decorated(*args, **kwargs) -> typing.Callable:
            for repeated in range(self.number_of_times_to_repeat):
                try:
                    logger.debug(f"repeat decorator executed for {repeated} time")
                    result = fn(*args, **kwargs)
                    return result
                except requests.RequestException as err:
                    logger.debug(
                        f"repeat decorator hit error for {repeated} time, error value for this try was {err}"  # noqa: E501
                    )
                    continue

        return decorated


class TikTokException(Exception):
    pass


class TikTokComments:
    @staticmethod
    def _check_response_status_codes(response):
        if response["status_code"] != 0:
            error = f'api returned error code: {response["status_code"]}, error message: {response["status_msg"]}'  # noqa: E501
            logger.debug(response)
            logger.exception(error)
            raise TikTokException(error)

    @staticmethod
    def _is_has_more_attribute_set_to_zero(response):
        if "has_more" in response:
            if response["has_more"] == 0:
                return True
        return False

    @staticmethod
    def _find_total_number_of_comments_for_video(video_id) -> int:
        comments = get(
            f"https://www.tiktok.com/api/comment/list/?aweme_id={video_id}&count=1&cursor=0",  # noqa: E501
            headers=HEADERS,
        ).json()
        TikTokComments._check_response_status_codes(comments)
        return comments["total"]

    @staticmethod
    @RepeatHttp500Errors(3)
    def _get_block_of_comments(video_id: int, cursor: int, count: int = 20) -> list:
        """
        Get a page of comments, the count is set to 20 as the api seems to
        not like a value higher than this.
        """
        comment_list: list = []

        comments = get(
            f"https://www.tiktok.com/api/comment/list/?aweme_id={video_id}&count={count}&cursor={cursor}",  # noqa: E501
            headers=HEADERS,
        ).json()

        logger.debug(f"raw response from server: {comments}")

        TikTokComments._check_response_status_codes(comments)

        if TikTokComments._is_has_more_attribute_set_to_zero(comments):
            logger.warning('comment block had the "has_more" attribute set to zero')
            return []

        [comment_list.append(comment) for comment in comments["comments"]]
        logger.debug(f"collected {len(comment_list)} for video_id {video_id}")
        return comment_list

    @staticmethod
    def get_comments_for_video_id(video_id):
        total_comments: int = TikTokComments._find_total_number_of_comments_for_video(
            video_id
        )  # noqa: E501
        cursor: int = 0

        comments = list()
        while total_comments > 0:
            block: list = TikTokComments._get_block_of_comments(video_id, cursor)
            if len(block) > 0:
                comments = comments + block
                cursor += 20
                total_comments -= 20
            else:
                break
        return comments


pprint.pprint(TikTokComments.get_comments_for_video_id("7095958860325833990"))
