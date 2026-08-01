import pr_agent.tools.pr_similar_issue as psi
from pr_agent.tools.pr_similar_issue import PRSimilarIssue


class FakeTokenHandler:
    def count_tokens(self, text):
        return len(text.split())


class FakeUser:
    def __init__(self, login):
        self.login = login


class FakeComment:
    def __init__(self, body):
        self.body = body


class FakeIssue:
    def __init__(self, number, title, body, comments=None, pull_request=None):
        self.number = number
        self.title = title
        self.body = body
        self.user = FakeUser("octocat")
        self.created_at = "2024-01-01"
        self.pull_request = pull_request
        self._comments = comments or []

    def get_comments(self):
        return self._comments


def _make_tool():
    tool = PRSimilarIssue.__new__(PRSimilarIssue)
    tool.max_issues_to_scan = 100
    tool.token_handler = FakeTokenHandler()
    return tool


def test_build_issues_corpus_skips_prs_and_includes_issue_and_long_comments(monkeypatch):
    monkeypatch.setattr(psi, "get_settings",
                        lambda: type("S", (), {"pr_similar_issue": type("P", (), {"skip_comments": False})}))
    tool = _make_tool()

    issues = [
        FakeIssue(1, "Bug", "Something broke", comments=[
            FakeComment("this is a sufficiently long comment about the bug behavior"),
            FakeComment("too short"),  # < 10 words -> skipped
        ]),
        FakeIssue(2, "A PR", "not an issue", pull_request={"url": "x"}),  # skipped
    ]

    corpus = tool._build_issues_corpus(issues, "org-repo")
    ids = [d.id for d in corpus.documents]

    assert ids[0] == "example_issue_org-repo"
    assert "issue_1.issue" in ids
    assert "issue_1.comment_1" in ids
    assert "issue_1.comment_2" not in ids  # short comment dropped
    assert not any(i.startswith("issue_2") for i in ids)  # PR skipped


def test_build_issues_corpus_respects_scan_limit(monkeypatch):
    monkeypatch.setattr(psi, "get_settings",
                        lambda: type("S", (), {"pr_similar_issue": type("P", (), {"skip_comments": True})}))
    tool = _make_tool()
    tool.max_issues_to_scan = 2

    issues = [FakeIssue(n, f"t{n}", f"body {n}") for n in range(10)]
    corpus = tool._build_issues_corpus(issues, "org-repo")
    issue_docs = [d for d in corpus.documents if d.id.endswith(".issue")]

    assert len(issue_docs) == 1  # stops once counter reaches max_issues_to_scan (2)


def test_embed_corpus_texts_batch_success(monkeypatch):
    class FakeEmbedding:
        @staticmethod
        def create(input, engine):
            return {"data": [{"embedding": [0.1, 0.2, 0.3]} for _ in input]}

    monkeypatch.setattr(psi.openai, "Embedding", FakeEmbedding)
    monkeypatch.setattr(psi, "get_settings",
                        lambda: type("S", (), {"openai": type("O", (), {"key": "k"})}))

    embeds = PRSimilarIssue._embed_corpus_texts(["a", "b"])
    assert embeds == [[0.1, 0.2, 0.3], [0.1, 0.2, 0.3]]


def test_embed_corpus_texts_falls_back_one_by_one_with_zero_vector(monkeypatch):
    class FakeEmbedding:
        @staticmethod
        def create(input, engine):
            if len(input) != 1:
                raise RuntimeError("batch failed")
            if input[0] == "bad":
                raise RuntimeError("single failed")
            return {"data": [{"embedding": [1.0]}]}

    monkeypatch.setattr(psi.openai, "Embedding", FakeEmbedding)
    monkeypatch.setattr(psi, "get_settings",
                        lambda: type("S", (), {"openai": type("O", (), {"key": "k"})}))

    embeds = PRSimilarIssue._embed_corpus_texts(["good", "bad"])
    assert embeds[0] == [1.0]
    assert embeds[1] == [0] * 1536
