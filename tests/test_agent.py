"""Agent loop: tool dispatch, history replay and the iteration guard."""

import json

from app.storage.models import ChatMessage

from .conftest import TELEGRAM_ID, make_completion, make_tool_call


async def test_plain_answer_needs_one_round_trip(agent, openai_client, tool_context):
    openai_client.chat.completions.create.return_value = make_completion("Hello there.")

    reply = await agent.reply(ctx=tool_context, prompt="hi")

    assert reply.text == "Hello there."
    assert reply.tool_calls == []
    assert openai_client.chat.completions.create.await_count == 1


async def test_tool_call_is_executed_and_fed_back(agent, openai_client, tool_context, repositories):
    openai_client.chat.completions.create.side_effect = [
        make_completion(
            None,
            [make_tool_call("call_1", "save_note", json.dumps({"text": "Landlord is Ana"}))],
        ),
        make_completion("Noted."),
    ]

    reply = await agent.reply(ctx=tool_context, prompt="remember my landlord is Ana")

    assert reply.text == "Noted."
    assert reply.tool_calls == ["save_note"]
    assert len(await repositories.notes.search(TELEGRAM_ID, "Ana")) == 1

    # Second call must carry assistant(tool_calls) followed by the tool result.
    second_call = openai_client.chat.completions.create.await_args_list[1]
    roles = [item["role"] for item in second_call.kwargs["messages"]]
    assert roles == ["system", "user", "assistant", "tool"]


async def test_parallel_tool_calls_all_run(agent, openai_client, tool_context):
    openai_client.chat.completions.create.side_effect = [
        make_completion(
            None,
            [
                make_tool_call("a", "save_note", json.dumps({"text": "one"})),
                make_tool_call("b", "save_note", json.dumps({"text": "two"})),
            ],
        ),
        make_completion("Both saved."),
    ]

    reply = await agent.reply(ctx=tool_context, prompt="remember one and two")

    assert reply.tool_calls == ["save_note", "save_note"]
    messages = openai_client.chat.completions.create.await_args_list[1].kwargs["messages"]
    assert [item["role"] for item in messages].count("tool") == 2


async def test_history_is_replayed_before_the_prompt(agent, openai_client, tool_context):
    openai_client.chat.completions.create.return_value = make_completion("ok")
    history = [
        ChatMessage(TELEGRAM_ID, "user", "my dog is called Rex"),
        ChatMessage(TELEGRAM_ID, "assistant", "Got it."),
    ]

    await agent.reply(ctx=tool_context, prompt="what is my dog called?", history=history)

    messages = openai_client.chat.completions.create.await_args_list[0].kwargs["messages"]
    assert [item["role"] for item in messages] == ["system", "user", "assistant", "user"]
    assert messages[1]["content"] == "my dog is called Rex"
    assert messages[-1]["content"] == "what is my dog called?"


async def test_tools_are_advertised_on_every_call(agent, openai_client, tool_context):
    openai_client.chat.completions.create.return_value = make_completion("ok")

    await agent.reply(ctx=tool_context, prompt="hi")

    kwargs = openai_client.chat.completions.create.await_args.kwargs
    assert {tool["function"]["name"] for tool in kwargs["tools"]} == {
        "get_weather",
        "save_note",
        "search_notes",
    }


async def test_loop_stops_at_max_iterations(agent, openai_client, tool_context):
    """A model that only ever calls tools must not spin forever."""
    openai_client.chat.completions.create.return_value = make_completion(
        None, [make_tool_call("loop", "search_notes", json.dumps({"query": "x"}))]
    )

    reply = await agent.reply(ctx=tool_context, prompt="loop forever")

    assert openai_client.chat.completions.create.await_count == 3  # max_iterations
    assert "narrow the request" in reply.text


async def test_empty_model_content_falls_back(agent, openai_client, tool_context):
    openai_client.chat.completions.create.return_value = make_completion("   ")

    reply = await agent.reply(ctx=tool_context, prompt="hi")

    assert reply.text
    assert "could not produce an answer" in reply.text
