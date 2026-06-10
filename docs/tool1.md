Responses API 支持使用方舟大模型内置工具、函数调用 Function Calling 等工具来扩展模型的功能。这些功能使模型能够搜索网络资料、图片处理、私域知识库搜索或者调用自定义函数。

<span id="07456946"></span>
## 快速开始

以天气查询场景为例，介绍使用函数调用 Function Calling 的方法。


<Tabs>
<Tab zoneid="EbmOdBCLdG" title="Curl">
<TabTitle>Curl</TabTitle>

**第一轮请求： 触发工具调用**

```Bash
curl https://ark.cn-beijing.volces.com/api/v3/responses \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "doubao-seed-2-0-lite-260215",
    "store": true,
    "input": [
        {
            "type": "message",
            "role": "user",
            "content": "查询北京今天的天气"
        }
    ],
    "tools": [
        {
            "type": "function",
            "name": "get_weather",
            "description": "根据城市名称查询该城市当日天气（含温度、天气状况）",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "城市名称，如北京、上海（仅支持国内地级市）"
                    }
                },
                "required": ["location"]
            }
        }
    ]
  }'
```


**第一轮响应：返回 function_call 指令**

模型会返回工具调用指令，关键字段为`call_id`（关联后续结果）、`arguments`（调用参数）：

```Python
{
    "created_at": 1756980000,
    "id": "resp_02175698000123456789abcdef0123",  # previous_response_id 
    "model": "doubao-seed-2-0-lite-260215",
    "object": "response",
    "output": [
        {
            "arguments": "{\"location\":\"北京\"}",  # Parameters automatically extracted by the model
            "call_id": "call_abc123def456ghi789jkl0",  # Unique invocation ID for result correlation
            "name": "get_weather",
            "type": "function_call",
            "id": "fc_02175698000abcdef0123456789gh",
            "status": "completed"
        }
    ],
    "status": "completed",
    "store": true,
    "expire_at": 1757239200
}
```


**执行工具：获取天气结果**

开发者根据 `arguments` 调用实际天气工具（如第三方天气API），假设返回结果为：

```Python
{
    "city": "北京",
    "date": "2025-10-13",
    "temperature": "18~28℃",
    "condition": "晴转多云",
    "wind": "东北风2级"
}
```


**第二轮请求：回传结果并生成最终响应**

传入上一轮 `response_id`、工具结果，模型生成自然语言回答：

```Python
curl https://ark.cn-beijing.volces.com/api/v3/responses \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "doubao-seed-2-0-lite-260215",
    "previous_response_id": "resp_02175698000123456789abcdef0123",  # Associate with the previous request
    "input": [
        {
            "type": "function_call_output",  # Return tool results
            "call_id": "call_abc123def456ghi789jkl0",   #  Consistent with the call_id of the instruction
            "output": "{\"city\":\"北京\",\"date\":\"2025-10-13\",\"temperature\":\"18~28℃\",\"condition\":\"晴转多云\",\"wind\":\"东北风2级\"}"
        }
    ]
  }'
```


**第二轮响应：生成最终回答**

模型结合工具结果，返回自然语言响应：

```JSON
{
    "created_at": 1756980100,
    "id": "resp_02175698010abcdef0123456789gh",
    "model": "doubao-seed-1-6-250615",
    "object": "response",
    "output": [
        {
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "output_text",
                    "text": "北京今天（2025-10-13）的天气为晴转多云，气温在18~28℃之间，东北风2级。"
                }
            ],
            "status": "completed",
            "id": "msg_02175698010abcdef0123456789ij"
        }
    ],
    "status": "completed",
    "store": true
}
```



</Tab>
<Tab zoneid="xeL2TkvwUC" title="Python">
<TabTitle>Python</TabTitle>

```Python
import os
from volcenginesdkarkruntime import Ark
import json

# Get API Key：https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
api_key = os.getenv('ARK_API_KEY')
client = Ark(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
)

# Define the tool (weather query tool)
weather_tool = [
    {
        "type": "function",
        "name": "get_weather",
        "description": "根据城市名称查询该城市当日天气（含温度、天气状况）",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "城市名称，如北京、上海（仅支持国内地级市）"
                }
            },
            "required": ["location"]
        }
    }
]

# ------------------- First Round Request: Trigger Tool Call -------------------
print("=== First Round Request: Trigger Tool Call ===")
first_response = client.responses.create(
    model="doubao-seed-2-0-lite-260215",
    store=True,
    input=[
        {
            "type": "message",
            "role": "user",
            "content": "查询北京今天的天气"
        }
    ],
    tools=weather_tool
)
# Extract key information（previous_response_id、call_id、arguments）
previous_response_id = first_response.id
function_call = next(
    item for item in first_response.output if item.type == "function_call"
)
call_id = function_call.call_id
call_arguments = function_call.arguments
print(f"First Round Response ID：{previous_response_id}")
print(f"Tool Call ID：{call_id}")
print(f"Call Parameters：{call_arguments}")

# ------------------- Simulate Tool Execution: Get Weather Results -------------------
print("=== Simulate Tool Execution: Get Weather Results ===")
# In real scenarios, call a third-party weather API here; we use mock data instead.
tool_output = {
    "city": "北京",
    "date": "2025-10-13",
    "temperature": "18~28℃",
    "condition": "晴转多云",
    "wind": "东北风2级"
}
print(f"Tool Return Result：{tool_output}")

# ------------------- Second Round Request: Return Result and Generate Final Response -------------------
print("=== Second Round Request: Return Result and Generate Final Response ===")
second_response = client.responses.create(
    model="doubao-seed-2-0-lite-260215",
    previous_response_id=previous_response_id,
    input=[
        {
            "type": "function_call_output",
            "call_id": call_id,
            "output": json.dumps(tool_output, ensure_ascii=False)
        }
    ]
)
# Extract and print the final answer
final_answer = next(
    item for item in second_response.output if item.type == "message"
)
print("=== Final Answer  ===")
print(final_answer.content[0].text)
```



</Tab>
<Tab zoneid="rRka1hoBl2" title="Go">
<TabTitle>Go</TabTitle>

```Go
package main

import (
    "context"
    "encoding/json"
    "fmt"
    "os"

    "github.com/volcengine/volcengine-go-sdk/service/arkruntime"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime/model/responses"
)

func main() {
    client := arkruntime.NewClientWithApiKey(
        os.Getenv("ARK_API_KEY"),
        arkruntime.WithBaseUrl("https://ark.cn-beijing.volces.com/api/v3"),
    )
    ctx := context.Background()
    des := "根据城市名称查询该城市当日天气（含温度、天气状况）"
    tools := []*responses.ResponsesTool{
        {
            Union: &responses.ResponsesTool_ToolFunction{
                ToolFunction: &responses.ToolFunction{
                    Name:        "get_weather",
                    Type:        responses.ToolType_function,
                    Description: &des,
                    Parameters:  &responses.Bytes{Value: []byte(`{"type":"object","properties":{"location":{"type":"string","description":"城市名称，如北京、上海（仅支持国内地级市）"}},"required":["location"]}`)},
                },
            },
        },
    }
    store := true
    resp, err := client.CreateResponses(ctx, &responses.ResponsesRequest{
        Model: "doubao-seed-2-0-lite-260215",
        Store: &store,
        Input: &responses.ResponsesInput{
            Union: &responses.ResponsesInput_ListValue{
                ListValue: &responses.InputItemList{ListValue: []*responses.InputItem{{
                    Union: &responses.InputItem_EasyMessage{
                        EasyMessage: &responses.ItemEasyMessage{
                            Role:    responses.MessageRole_user,
                            Type:    responses.ItemType_message.Enum(),
                            Content: &responses.MessageContent{Union: &responses.MessageContent_StringValue{StringValue: "北京的天气怎么样？"}},
                        },
                    },
                }}},
            },
        },
        Tools: tools,
    })
    if err != nil {
        fmt.Printf("response error: %v", err)
        return
    }
    fmt.Println("===First Round Request: Trigger Tool Call=====")
    fmt.Println(resp)
    // Extract key information（previous_response_id、call_id、arguments）
    previous_response_id := resp.Id
    function_call := resp.Output[len(resp.Output)-1].GetFunctionToolCall()
    call_id := function_call.CallId
    call_arguments := function_call.Arguments
    fmt.Println("id", previous_response_id)
    fmt.Println("call_id", call_id)
    fmt.Println("call_arguments", call_arguments)
    fmt.Println("=== imulate Tool Execution: Get Weather Results ===")
    // In real scenarios, call a third-party weather API here; we use mock data instead.
    tool_output := map[string]string{
        "city": "北京",
        "date": "2025-10-13",
        "temperature": "18~28℃",
        "condition": "晴转多云",
        "wind": "东北风2级"
    }
    json_output, json_err := json.Marshal(tool_output)
    if json_err != nil {
        fmt.Printf("json marshal error: %v", json_err)
        return
    }
    fmt.Println("Tool Return Result：", tool_output)
    fmt.Println("=== Second Round Request: Return Result and Generate Final Response ====")

    message := &responses.ResponsesInput{
        Union: &responses.ResponsesInput_ListValue{
            ListValue: &responses.InputItemList{ListValue: []*responses.InputItem{
                {
                    Union: &responses.InputItem_FunctionToolCallOutput{
                        FunctionToolCallOutput: &responses.ItemFunctionToolCallOutput{
                            CallId: call_id,
                            Output: string(json_output),
                            Type:   responses.ItemType_function_call_output,
                        },
                    },
                },
            }},
        },
    }
    second_resp, secod_err := client.CreateResponses(ctx, &responses.ResponsesRequest{
        Model:              "doubao-seed-2-0-lite-260215",
        PreviousResponseId: &previous_response_id,
        Input:              message,
    })
    if secod_err != nil {
        fmt.Printf("response error: %v", secod_err)
        return
    }
    fmt.Println(second_resp)
}
```



</Tab>
<Tab zoneid="N0pQW4Jhvs" title="Java">
<TabTitle>Java</TabTitle>

```Java
package com.ark.example;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.volcengine.ark.runtime.model.responses.item.*;
import com.volcengine.ark.runtime.service.ArkService;
import com.volcengine.ark.runtime.model.responses.request.*;
import com.volcengine.ark.runtime.model.responses.response.ResponseObject;
import com.volcengine.ark.runtime.model.responses.constant.ResponsesConstants;
import com.volcengine.ark.runtime.model.responses.content.InputContentItemText;
import com.volcengine.ark.runtime.model.responses.tool.ResponsesTool;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.volcengine.ark.runtime.model.responses.tool.ToolFunction;
import com.fasterxml.jackson.databind.JsonNode;
import java.util.*;

public class demo {
    public static ObjectMapper om = new ObjectMapper();
    public static List<ResponsesTool> buildTools() {
        JsonNode params = om.createObjectNode()
                .put("type", "object")
                .set("properties", om.createObjectNode()
                        .set("location", om.createObjectNode()
                                .put("type", "string")
                                .put("description", "城市名称，如北京、上海（仅支持国内地级市）")));

        ToolFunction t = ToolFunction.builder()
                .name("get_weather")
                .description("根据城市名称查询该城市当日天气（含温度、天气状况）")
                .parameters(params)
                .build();

        return Arrays.asList(t);
    }
    public static void main(String[] args) throws JsonProcessingException {
        String apiKey = System.getenv("ARK_API_KEY");

        ArkService arkService = ArkService.builder().apiKey(apiKey).baseUrl("https://ark.cn-beijing.volces.com/api/v3").build();
        System.out.println("=== First Round Request: Trigger Tool Call ===");
        CreateResponsesRequest req = CreateResponsesRequest.builder()
                .model("doubao-seed-2-0-lite-260215")
                .store(true)
                .input(ResponsesInput.builder().addListItem(
                        ItemEasyMessage.builder().role(ResponsesConstants.MESSAGE_ROLE_USER).content(
                                MessageContent.builder()
                                        .addListItem(InputContentItemText.builder().text("查询北京今天的天气").build())
                                        .build()
                        ).build()
                ).build())
                .tools(buildTools())
                .build();
        ResponseObject resp = arkService.createResponse(req);
        System.out.println(resp);
        // Extract key information（previous_response_id、call_id、arguments）
        String previousId = resp.getId();
        BaseItem targetCall = null;
        for(BaseItem item : resp.getOutput()) {
            if ("function_call".equals(item.getType())) {
                targetCall = item;
                break;
            }
        }
        ObjectMapper objectMapper = new ObjectMapper();
        String jsonStr = objectMapper.writeValueAsString(targetCall);
        ItemFunctionToolCall functionCall = objectMapper.readValue(jsonStr, ItemFunctionToolCall.class);
        String callId = functionCall.getCallId();
        String callArguments = functionCall.getArguments();
        System.out.println("First Round Response ID:" + previousId);
        System.out.println("Tool Call ID:" + callId);
        System.out.println("Call Parameters:" + callArguments);

        System.out.println("=== Simulate Tool Execution: Get Weather Results  ===");
        Map<String, String> toolOutput = new HashMap<String, String>() {{
            put("city", "北京");
            put("date", "2025-10-13");
            put("temperature", "18~28℃");
            put("condition", "晴转多云");
            put("wind", "东北风2级");
        }};

        System.out.println(toolOutput);

        System.out.println("=== Second Round Request: Return Result and Generate Final Response ===");
        CreateResponsesRequest secondReq = CreateResponsesRequest.builder()
                .model("doubao-seed-2-0-lite-260215")
                .previousResponseId(previousId)
                .input(ResponsesInput.builder()
                        .addListItem(ItemFunctionToolCallOutput.builder().callId(callId).output(objectMapper.writeValueAsString(toolOutput)).build())
                    .build())
                .tools(buildTools())
                .build();
        ResponseObject secondResp = arkService.createResponse(secondReq);
        System.out.println("=== Final Answer ===");
        System.out.println(secondResp);
        arkService.shutdownExecutor();
    }
}
```



</Tab>
<Tab zoneid="xvshw7gfqO" title="OpenAI SDK">
<TabTitle>OpenAI SDK</TabTitle>

```Python
import os
from openai import OpenAI
import json

# Get API Key：https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
api_key = os.getenv('ARK_API_KEY')
client = OpenAI(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
)

# Define the tool (weather query tool)
weather_tool = [
    {
        "type": "function",
        "name": "get_weather",
        "description": "根据城市名称查询该城市当日天气（含温度、天气状况）",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "城市名称，如北京、上海（仅支持国内地级市）"
                }
            },
            "required": ["location"]
        }
    }
]

# ------------------- First Round Request: Trigger Tool Call -------------------
print("=== First Round Request: Trigger Tool Call ===")
first_response = client.responses.create(
    model="doubao-seed-2-0-lite-260215",
    store=True,
    input=[
        {
            "type": "message",
            "role": "user",
            "content": "查询北京今天的天气"
        }
    ],
    tools=weather_tool
)
# Extract key information（previous_response_id、call_id、arguments）
previous_response_id = first_response.id
function_call = next(
    item for item in first_response.output if item.type == "function_call"
)
call_id = function_call.call_id
call_arguments = function_call.arguments
print(f"First Round Response ID：{previous_response_id}")
print(f"Tool Call ID：{call_id}")
print(f"Call Parameters：{call_arguments}")

# ------------------- Simulate Tool Execution: Get Weather Results -------------------
print("=== Simulate Tool Execution: Get Weather Results ===")
tool_output = {
    "city": "北京",
    "date": "2025-10-13",
    "temperature": "18~28℃",
    "condition": "晴转多云",
    "wind": "东北风2级"
}
print(f"Tool Return Result：{tool_output}")

# ------------------- Second Round Request: Return Result and Generate Final Response-------------------
print("=== Second Round Request: Return Result and Generate Final Response ===")
second_response = client.responses.create(
    model="doubao-seed-2-0-lite-260215",
    previous_response_id=previous_response_id,
    input=[
        {
            "type": "function_call_output",
            "call_id": call_id,
            "output": json.dumps(tool_output, ensure_ascii=False)
        }
    ]
)
# Extract and print the final answer
final_answer = next(
    item for item in second_response.output if item.type == "message"
)
print("=== Final Answer ===")
print(final_answer.content[0].text)
```



</Tab>
</Tabs>


<span id="633a560f"></span>
## 支持工具

<span id="960a125c"></span>
### 内置工具

当通过 Responses API [创建模型响应](https://www.volcengine.com/docs/82379/1569618)时，您可以通过在参数中配置`tools`字段来访问工具。每个工具中都有独特的配置要求，具体见如下教程：


* [联网搜索 Web Search](https://www.volcengine.com/docs/82379/1756990)

   支持获取实时公开网络信息（如新闻、商品、天气等），解决数据时效性、知识盲区、信息同步等核心问题，并且无需自行开发搜索引擎或维护数据资源。

* [图像处理 Image Process](https://www.volcengine.com/docs/82379/1798161)

   支持通过 Responses API 调用对输入图片执行画点、画线、旋转、缩放、框选/裁剪关键区域等基础操作，适用于需模型通过视觉处理提升图片理解的场景（如图文内容分析、物体定位标注、多轮视觉推理等）。工具通过模型自动判断图像处理逻辑，支持与自定义 Function 混合使用，且可处理多轮视觉输入（上一轮输出图片作为下一轮输入）。

* [私域知识库搜索 Knowledge Search](https://www.volcengine.com/docs/82379/1873396)

   支持通过 Responses API 调用直接获取企业私域知识库中的信息（如内部文档、产品手册、行业资料等），适用于需基于企业专属数据解答问题的场景（如内部培训问答、产品功能咨询、行业方案查询等）。工具通过模型自动判断是否需要调用私域知识库，支持与自定义 Function、MCP 等工具混合使用，目前仅支持旗舰版知识库。


<span id="2f52557d"></span>
### 函数调用 Function Calling

可以在创建模型响应时，使用`tools`来定义自定义函数。模型通过调用自定义函数代码，来访问模型中无法直接使用的特定数据或功能。了解更多信息，请参见[函数调用 Function Calling](https://www.volcengine.com/docs/82379/1262342)。

<span id="f8cd1de5"></span>
### 云部署 MCP / Remote MCP

对接“[MCP MarketPlace](https://www.volcengine.com/mcp-marketplace)”，支持调用市场内各类垂直领域MCP工具（如巨量千川、知识库），无需自行开发工具逻辑。适用于复杂任务（如多步数据查询 + 分析）场景，支持与自定义 Function、Web Search 工具混合使用。具体教程查看[云部署 MCP / Remote MCP](https://www.volcengine.com/docs/82379/1827534)。



