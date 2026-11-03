import pytest
from backend.agent import TaskManagementAgent
from backend.task_crud import get_task_crud

def test_agent_workshop_scenario():
    agent = TaskManagementAgent()
    crud = get_task_crud()
    initial_count = len(crud.list_tasks())

    user_request = (
        "Create tasks for preparing the workshop: order catering with vegan and peanut allergy options, "
        "test the AV equipment in room 302, get the speaker slides, and print the attendee badges by next Wednesday."
    )

    # 1. Process initial request - should produce proposal, NOT create tasks yet
    response = agent.process_request(user_request)
    assert response.proposal is not None
    assert response.created_tasks is None
    assert len(response.proposal.proposed_tasks) >= 3

    # Check that ChromaDB enriched the tasks with specific note details
    catering_tasks = [t for t in response.proposal.proposed_tasks if "cater" in t.title.lower() or "cater" in t.category.lower()]
    assert len(catering_tasks) > 0
    cat_desc = catering_tasks[0].description
    assert "GreenLeaf" in cat_desc or "Vegan" in cat_desc or "allergy" in cat_desc

    # Check AV equipment task
    av_tasks = [t for t in response.proposal.proposed_tasks if "av" in t.title.lower() or "room 302" in t.title.lower() or "av" in t.category.lower()]
    assert len(av_tasks) > 0
    assert "302" in av_tasks[0].description or "projector" in av_tasks[0].description

    # Ensure no tasks were prematurely created in the DB
    assert len(crud.list_tasks()) == initial_count

    # 2. Confirm and create tasks
    confirm_response = agent.confirm_and_create_tasks(response.proposal.proposed_tasks)
    assert confirm_response.created_tasks is not None
    assert len(confirm_response.created_tasks) == len(response.proposal.proposed_tasks)

    # Now verify DB has the new tasks
    new_tasks = crud.list_tasks()
    assert len(new_tasks) == initial_count + len(confirm_response.created_tasks)

if __name__ == "__main__":
    pytest.main(["-v", __file__])
