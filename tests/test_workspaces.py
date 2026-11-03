def create_workspace(client, headers, name="Brain"):
    response = client.post("/api/v1/workspaces", headers=headers, json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_workspace_isolation(client, account):
    owner = account()
    outsider = account("other@example.com")
    workspace = create_workspace(client, owner)
    assert len(client.get("/api/v1/workspaces", headers=owner).json()) == 1
    assert client.get("/api/v1/workspaces", headers=outsider).json() == []
    for suffix in ("", "/members", "/audit"):
        response = client.get(f"/api/v1/workspaces/{workspace}{suffix}", headers=outsider)
        assert response.status_code == 404
    assert (
        client.post(
            f"/api/v1/workspaces/{workspace}/members",
            headers=outsider,
            json={"email": "other@example.com"},
        ).status_code
        == 404
    )


def test_viewer_cannot_administer_or_read_audit(client, account):
    owner = account()
    viewer = account("viewer@example.com")
    workspace = create_workspace(client, owner)
    path = f"/api/v1/workspaces/{workspace}"
    assert (
        client.post(
            path + "/members",
            headers=owner,
            json={
                "email": "viewer@example.com",
                "role": "viewer",
            },
        ).status_code
        == 201
    )
    assert client.get(path, headers=viewer).status_code == 200
    assert client.get(path + "/members", headers=viewer).status_code == 200
    assert client.get(path + "/audit", headers=viewer).status_code == 403
    assert (
        client.post(
            path + "/members",
            headers=viewer,
            json={
                "email": "owner@example.com",
                "role": "admin",
            },
        ).status_code
        == 403
    )
    events = client.get(path + "/audit", headers=owner).json()
    assert {e["action"] for e in events} == {"workspace.created", "member.added"}


def test_role_grants_and_duplicate_members(client, account):
    owner = account()
    admin = account("admin@example.com")
    account("member@example.com")
    workspace = create_workspace(client, owner)
    path = f"/api/v1/workspaces/{workspace}/members"
    assert (
        client.post(
            path,
            headers=owner,
            json={
                "email": "admin@example.com",
                "role": "admin",
            },
        ).status_code
        == 201
    )
    for role in ("owner", "admin"):
        assert (
            client.post(
                path,
                headers=admin,
                json={
                    "email": "member@example.com",
                    "role": role,
                },
            ).status_code
            == 403
        )
    assert (
        client.post(
            path,
            headers=admin,
            json={
                "email": "member@example.com",
                "role": "member",
            },
        ).status_code
        == 201
    )
    assert (
        client.post(
            path,
            headers=admin,
            json={
                "email": "member@example.com",
                "role": "member",
            },
        ).status_code
        == 409
    )
    assert (
        client.post(
            path,
            headers=owner,
            json={
                "email": "member@example.com",
                "role": "owner",
            },
        ).status_code
        == 403
    )


def test_public_payload_cannot_set_commercial_plan(client, account):
    headers = account()
    assert (
        client.post(
            "/api/v1/workspaces",
            headers=headers,
            json={
                "name": "Brain",
                "plan": "enterprise",
            },
        ).status_code
        == 422
    )
    create_workspace(client, headers, "One")
    create_workspace(client, headers, "Two")
    assert len(client.get("/api/v1/workspaces?limit=1&offset=1", headers=headers).json()) == 1
    assert client.get("/api/v1/workspaces?limit=101", headers=headers).status_code == 422
