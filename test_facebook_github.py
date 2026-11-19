import http.client
import json
import unittest
from unittest.mock import MagicMock, patch

from tools.facebook_github import GithubAPI, GithubError, check_approval, reserve, record_received


BASE = "a" * 40
TREE = "b" * 40
RESERVATION = "c" * 40
SCHEDULED = "d" * 40
DIGEST = "e" * 64
REF = "heads/facebook-reservas/p123/a148"
ROOT = "/repos/owner/repo"


class FakeAPI:
    repository = "owner/repo"

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def confirmation(sha, ref=REF):
    return {"ref": "refs/" + ref, "object": {"sha": sha}}


def review(**changes):
    data = {"environments": [{"name": "facebook"}], "state": "approved",
            "user": {"id": 42}, "comment": "  APROVO " + DIGEST + "\n"}
    data.update(changes)
    return data


class ApprovalTests(unittest.TestCase):
    def check(self, records, status=200):
        api = FakeAPI([(status, records)])
        check_approval(api, "1234", "facebook", 42, DIGEST)
        self.assertEqual(api.calls, [("GET", ROOT + "/actions/runs/1234/approvals", None)])

    def test_approved(self):
        self.check([review(), review(environments=[{"name": "outro"}])])

    def test_missing_wrong_or_multiple_approvals_fail(self):
        variants = [[], [review(user={"id": 43})],
                    [review(comment="APROVO " + "f" * 64)],
                    [review(), review()], [review(state="rejected")],
                    [review(environments=[{"name": "Facebook"}])],
                    [review(user={"id": True})], [None], {}, None]
        for records in variants:
            with self.subTest(records=records), self.assertRaises(GithubError):
                self.check(records)
        with self.assertRaises(GithubError):
            self.check([review()], 403)

    def test_invalid_inputs_do_not_call_api(self):
        for run_id, digest in [("1/../2", DIGEST), ("1", "x" * 64), ("1", "e" * 63)]:
            api = FakeAPI([])
            with self.subTest(run_id=run_id, digest=digest), self.assertRaises(GithubError):
                check_approval(api, run_id, "facebook", 42, digest)
            self.assertEqual(api.calls, [])


class ReservationTests(unittest.TestCase):
    def responses(self):
        return [(200, {"tree": {"sha": TREE}}), (201, {"sha": RESERVATION}),
                (201, confirmation(RESERVATION))]

    def test_reservation_and_scheduling(self):
        api = FakeAPI(self.responses() + [(200, {"tree": {"sha": TREE}}),
                      (201, {"sha": SCHEDULED}), (200, confirmation(SCHEDULED))])
        ref, sha = reserve(api, "123", "148", DIGEST, "55", BASE)
        self.assertEqual((ref, sha), (REF, RESERVATION))
        self.assertEqual(api.calls[0], ("GET", ROOT + "/git/commits/" + BASE, None))
        method, path, commit = api.calls[1]
        self.assertEqual((method, path), ("POST", ROOT + "/git/commits"))
        self.assertEqual(commit["tree"], TREE)
        self.assertEqual(commit["parents"], [BASE])
        self.assertEqual(json.loads(commit["message"]), {
            "estado": "RESERVADO", "rede": "facebook", "page_id": "123",
            "article_number": "148", "digest": DIGEST, "run_id": "55"})
        self.assertEqual(api.calls[2], ("POST", ROOT + "/git/refs",
                                       {"ref": "refs/" + REF, "sha": RESERVATION}))
        record_received(api, ref, sha, "123_456")
        self.assertEqual(api.calls[3], ("GET", ROOT + "/git/commits/" + RESERVATION, None))
        commit = api.calls[4][2]
        self.assertEqual(commit["parents"], [RESERVATION])
        self.assertEqual(commit["tree"], TREE)
        self.assertEqual(json.loads(commit["message"]), {"estado": "ID_RECEBIDO", "remote_id": "123_456"})
        self.assertEqual(api.calls[5], ("PATCH", ROOT + "/git/refs/" + REF,
                                       {"sha": SCHEDULED, "force": False}))

    def test_conflicts_ambiguous_results_and_mismatches_fail_without_retry(self):
        for result in [(422, {"message": "already exists"}), (500, {}),
                       (201, confirmation(BASE)), (201, confirmation(RESERVATION, "heads/other")),
                       GithubError("ambigua")]:
            api = FakeAPI(self.responses()[:2] + [result])
            with self.subTest(result=result), self.assertRaises(GithubError):
                reserve(api, "123", "148", DIGEST, "55", BASE)
            self.assertEqual(len(api.calls), 3)
            self.assertTrue(all("github" not in call[1] and "meta" not in call[1] for call in api.calls))

    def test_article_147_blocked_for_every_page_including_zero_prefix(self):
        for page, article in [("1", "147"), ("999", "000147")]:
            api = FakeAPI([])
            with self.subTest(page=page, article=article), self.assertRaises(GithubError):
                reserve(api, page, article, DIGEST, "55", BASE)
            self.assertEqual(api.calls, [])

    def test_invalid_reservation_inputs(self):
        for args in [("1/2", "148", DIGEST, "55", BASE), ("1", "148x", DIGEST, "55", BASE),
                     ("1", "148", "x" * 64, "55", BASE), ("1", "148", DIGEST, "-1", BASE),
                     ("1", "148", DIGEST, "55", "a" * 39),
                     ("01", "148", DIGEST, "55", BASE), ("1", "0148", DIGEST, "55", BASE)]:
            api = FakeAPI([])
            with self.subTest(args=args), self.assertRaises(GithubError):
                reserve(api, *args)
            self.assertEqual(api.calls, [])

    def test_scheduling_failure_never_retries_or_deletes(self):
        for result in [(422, {}), (200, confirmation(BASE)), GithubError("ambigua")]:
            api = FakeAPI([(200, {"tree": {"sha": TREE}}), (201, {"sha": SCHEDULED}), result])
            with self.subTest(result=result), self.assertRaises(GithubError):
                record_received(api, REF, RESERVATION, "123_456")
            self.assertEqual([call[0] for call in api.calls], ["GET", "POST", "PATCH"])
            self.assertFalse(api.calls[-1][2]["force"])

    def test_invalid_remote_identifier_or_reference(self):
        for ref, remote in [(REF, "abc"), (REF, "12__34"), (REF, "12_"),
                            ("heads/master", "1"), ("heads/facebook-reservas/p1/a147", "1")]:
            api = FakeAPI([])
            with self.subTest(ref=ref, remote=remote), self.assertRaises(GithubError):
                record_received(api, ref, RESERVATION, remote)
            self.assertEqual(api.calls, [])

    def test_bad_tree_or_commit_fails_before_ref(self):
        for responses in [[(200, {})], [(404, {})],
                          [(200, {"tree": {"sha": TREE}}), (201, {"sha": "invalid"})]]:
            api = FakeAPI(responses)
            with self.subTest(responses=responses), self.assertRaises(GithubError):
                reserve(api, "123", "148", DIGEST, "55", BASE)
            self.assertTrue(all(call[1] != ROOT + "/git/refs" for call in api.calls))


class TransportTests(unittest.TestCase):
    @patch("tools.facebook_github.http.client.HTTPSConnection")
    def test_https_headers_json_no_redirect_and_no_call_on_init(self, connection):
        response = MagicMock(status=302)
        response.read.return_value = b'{"message":"redirect"}'
        connection.return_value.getresponse.return_value = response
        api = GithubAPI("owner/repo", "secret")
        connection.assert_not_called()
        self.assertEqual(api.request("POST", "/repos/owner/repo/git/refs", {"a": 1}),
                         (302, {"message": "redirect"}))
        connection.assert_called_once_with("api.github.com", timeout=15)
        args, kwargs = connection.return_value.request.call_args
        self.assertEqual(args, ("POST", "/repos/owner/repo/git/refs"))
        self.assertEqual(json.loads(kwargs["body"]), {"a": 1})
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer secret")
        connection.return_value.close.assert_called_once()

    @patch("tools.facebook_github.http.client.HTTPSConnection")
    def test_errors_are_sanitized(self, connection):
        api = GithubAPI("owner/repo", "secret")
        for failure in [OSError("secret body"), http.client.HTTPException("secret body")]:
            connection.side_effect = failure
            with self.subTest(failure=failure), self.assertRaises(GithubError) as caught:
                api.request("GET", "/test")
            self.assertNotIn("secret", str(caught.exception))
            self.assertIsNone(caught.exception.__cause__)
        connection.side_effect = None
        connection.return_value.getresponse.return_value.read.return_value = b"secret invalid json"
        with self.assertRaises(GithubError) as caught:
            api.request("GET", "/test")
        self.assertNotIn("secret", str(caught.exception))

    def test_invalid_repositories_and_paths(self):
        for repo in ["../repo", "owner/repo/extra", "owner/..", "owner/repo?x", "owner/repo\n"]:
            with self.subTest(repo=repo), self.assertRaises(GithubError):
                GithubAPI(repo, "token")
        api = GithubAPI("owner/repo", "token")
        for method, path in [("DELETE", "/test"), ("GET", "//evil"), ("GET", "/test\r\n")]:
            with self.subTest(method=method, path=path), self.assertRaises(GithubError):
                api.request(method, path)


if __name__ == "__main__":
    unittest.main()
