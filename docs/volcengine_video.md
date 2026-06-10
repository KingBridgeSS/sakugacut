视觉大模型可理解视频中的视觉信息，完成如描述其中的物体、分析动作逻辑等视觉相关任务，可用于自动化视频内容审核、智能监控分析等，大幅节省人工成本，适用于智能安防、体育赛事分析、媒体内容管理等领域。这篇教程帮助您通过 API 完成含视频输入的各类任务。

<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>


<div data-tips="true" data-tips-type="tip">方舟平台的新用户？获取 API Key 及 开通模型等准备工作，请参见 <a href="https://www.volcengine.com/docs/82379/1399008">快速入门</a>。</div>


<span id="31778cb5"></span>
# 支持模型

请参见[视觉理解能力](https://www.volcengine.com/docs/82379/1330310#ff5ef604)。

<span id="f8d6cc48"></span>
# API 接口


* [Responses API](https://www.volcengine.com/docs/82379/1569618)：支持视频作为输入进行分析。支持 File ID 方式进行视频理解，使用方式参见[Files API 上传（推荐）](https://www.volcengine.com/docs/82379/1895586#35d3ebc5)。

* [Chat API](https://www.volcengine.com/docs/82379/1494384)：支持视频作为输入进行分析。


<span id="547c81e8"></span>
# 视频传入方式

支持的视频文件传入方式如下：


* 本地文件上传：

   * [Files API 上传（推荐）](https://www.volcengine.com/docs/82379/1895586#35d3ebc5)：直接传入本地文件，视频文件大小不能超过 512 MB，适用于在多个请求中重复使用文件的场景。

   * [Base64 编码传入](https://www.volcengine.com/docs/82379/1895586#22314028)：适用于文件体积较小的场景，视频文件小于 50 MB，请求体不能超过 64 MB。

* [视频 URL 传入](https://www.volcengine.com/docs/82379/1895586#8e3a48ed)：适用于文件已存在公网可访问 URL 的场景，视频文件大小不能超过 50 MB。


<span id="a8d59104"></span>
## 本地文件上传

<span id="35d3ebc5"></span>
### Files API 上传（推荐）

建议优先使用 Files API 上传本地文件，不仅可以支持最大 512MB 文件的处理，还可以避免请求时重新上传内容，减少预处理导致的时延，同时可在多次请求中重复使用，节省公网下载时延。（当前Responses API支持该方式。）


> * 该方式上传的文件默认存储 7 天，存储有效期取值范围为1\-30天。

> * 如果需要实时获取分析内容，或者要规避复杂任务引发的客户端超时失败问题，可采用流式输出的方式，具体示例见[流式输出](https://www.volcengine.com/docs/82379/1895586#5cfd1f60)。



<Tabs>
<Tab zoneid="SyFRAWyudU" title="Curl">
<TabTitle>Curl</TabTitle>

1. 上传视频文件获取File ID。

   ```Bash
   curl https://ark.cn-beijing.volces.com/api/v3/files \
   -H "Authorization: Bearer $ARK_API_KEY" \
   -F 'purpose=user_data' \
   -F 'file=@/Users/doc/demo.mp4' \
   -F 'preprocess_configs[video][fps]=0.3'
   ```
   

2. 在Responses API中引用File ID。

   ```Bash
   curl https://ark.cn-beijing.volces.com/api/v3/responses \
   -H "Authorization: Bearer $ARK_API_KEY" \
   -H 'Content-Type: application/json' \
   -d '{
       "model": "doubao-seed-2-0-lite-260215",
       "input": [
           {
               "role": "user",
               "content": [
                   {
                       "type": "input_video",
                       "file_id": "file-20251018****"
                   },
                   {
                       "type": "input_text",
                       "text": "请你描述下视频中的人物的一系列动作，以JSON格式输出开始时间（start_time）、结束时间（end_time）、事件（event）、是否危险（danger），请使用HH:mm:ss表示时间戳。"
                   }
               ]
           }
       ]
   }'
   ```
   


</Tab>
<Tab zoneid="ivUCCPeb7q" title="Python">
<TabTitle>Python</TabTitle>

```Python
import asyncio
import os
from volcenginesdkarkruntime import AsyncArk

client = AsyncArk(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=os.getenv('ARK_API_KEY')
)

async def main():
    # upload video file
    print("Upload video file")
    file = await client.files.create(
        # replace with your local video path
        file=open("/Users/doc/demo.mp4", "rb"),
        purpose="user_data",
        preprocess_configs={
            "video": {
                "fps": 0.3,  # define the sampling fps of the video, default is 1.0
            }
        }
    )
    print(f"File uploaded: {file.id}")

    # Wait for the file to finish processing
    await client.files.wait_for_processing(file.id)
    print(f"File processed: {file.id}")

    response = await client.responses.create(
        model="doubao-seed-2-0-lite-260215",
        input=[
            {"role": "user", "content": [
                {
                    "type": "input_video",
                    "file_id": file.id  # ref video file id
                },
                {
                    "type": "input_text",
                    "text": "请你描述下视频中的人物的一系列动作，以JSON格式输出开始时间（start_time）、结束时间（end_time）、事件（event）、是否危险（danger），请使用HH:mm:ss表示时间戳。"
                    
                }
            ]},
        ]
    )
    print(response)

if __name__ == "__main__":
    asyncio.run(main())
```



</Tab>
<Tab zoneid="rhZfVlM8JD" title="Go">
<TabTitle>Go</TabTitle>

```Go
package main

import (
    "context"
    "fmt"
    "io"
    "os"
    "time"

    "github.com/volcengine/volcengine-go-sdk/service/arkruntime"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime/model/file"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime/model/responses"
    "github.com/volcengine/volcengine-go-sdk/volcengine"
)

func main() {
    client := arkruntime.NewClientWithApiKey(
        // Get API Key：https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
        os.Getenv("ARK_API_KEY"),
        arkruntime.WithBaseUrl("https://ark.cn-beijing.volces.com/api/v3"),
    )
    ctx := context.Background()

    fmt.Println("----- upload video data -----")
    data, err := os.Open("/Users/doc/demo.mp4")
    if err != nil {
        fmt.Printf("read file error: %v\n", err)
        return
    }
    fileInfo, err := client.UploadFile(ctx, &file.UploadFileRequest{
        File:    data,
        Purpose: file.PurposeUserData,
        PreprocessConfigs: &file.PreprocessConfigs{
            Video: &file.Video{
                Fps: volcengine.Float64(0.3),
            },
        },
    })

    if err != nil {
        fmt.Printf("upload file error: %v", err)
        return
    }

    // Wait for the file to finish processing
    for fileInfo.Status == file.StatusProcessing {
        fmt.Println("Waiting for video to be processed...")
        time.Sleep(2 * time.Second)
        fileInfo, err = client.RetrieveFile(ctx, fileInfo.ID) // update file info
        if err != nil {
            fmt.Printf("get file status error: %v", err)
            return
        }
    }
    fmt.Printf("Video processing completed: %s, status: %s\n", fileInfo.ID, fileInfo.Status)
    inputMessage := &responses.ItemInputMessage{
        Role: responses.MessageRole_user,
        Content: []*responses.ContentItem{
            {
                Union: &responses.ContentItem_Video{
                    Video: &responses.ContentItemVideo{
                        Type:   responses.ContentItemType_input_video,
                        FileId: volcengine.String(fileInfo.ID),
                    },
                },
            },
            {
                Union: &responses.ContentItem_Text{
                    Text: &responses.ContentItemText{
                        Type: responses.ContentItemType_input_text,
                        Text: "请你描述下视频中的人物的一系列动作，以JSON格式输出开始时间（start_time）、结束时间（end_time）、事件（event）、是否危险（danger），请使用HH:mm:ss表示时间戳。",
                    },
                },
            },
        },
    }
    createResponsesReq := &responses.ResponsesRequest{
        Model: "doubao-seed-2-0-lite-260215",
        Input: &responses.ResponsesInput{
            Union: &responses.ResponsesInput_ListValue{
                ListValue: &responses.InputItemList{ListValue: []*responses.InputItem{{
                    Union: &responses.InputItem_InputMessage{
                        InputMessage: inputMessage,
                    },
                }}},
            },
        },
        Caching: &responses.ResponsesCaching{Type: responses.CacheType_enabled.Enum()},
    }

    resp, err := client.CreateResponses(ctx, createResponsesReq)
    if err != nil {
        fmt.Printf("stream error: %v\n", err)
        return
    }
    fmt.Println(resp)
}
```



</Tab>
<Tab zoneid="W9teYv661H" title="Java">
<TabTitle>Java</TabTitle>

```Java
package com.ark.sample;

import com.volcengine.ark.runtime.model.files.FileMeta;
import com.volcengine.ark.runtime.model.files.PreprocessConfigs;
import com.volcengine.ark.runtime.model.files.UploadFileRequest;
import com.volcengine.ark.runtime.model.files.Video;
import com.volcengine.ark.runtime.service.ArkService;
import com.volcengine.ark.runtime.model.responses.request.*;
import com.volcengine.ark.runtime.model.responses.item.ItemEasyMessage;
import com.volcengine.ark.runtime.model.responses.constant.ResponsesConstants;
import com.volcengine.ark.runtime.model.responses.item.MessageContent;
import com.volcengine.ark.runtime.model.responses.content.InputContentItemVideo;
import com.volcengine.ark.runtime.model.responses.content.InputContentItemText;
import com.volcengine.ark.runtime.model.responses.response.ResponseObject;
import java.io.File;
import java.util.concurrent.TimeUnit;

public class demo {
    public static void main(String[] args) {
        String apiKey = System.getenv("ARK_API_KEY");
        ArkService service = ArkService.builder().apiKey(apiKey).baseUrl("https://ark.cn-beijing.volces.com/api/v3").build();

        System.out.println("===== Upload File Example=====");
        // upload a video for responses
        FileMeta fileMeta;
        fileMeta = service.uploadFile(
                UploadFileRequest.builder().
                        file(new File("/Users/doc/demo.mp4")) // replace with your image file path
                        .purpose("user_data")
                        .preprocessConfigs(PreprocessConfigs.builder().video(new Video(0.3)).build())
                        .build());
        System.out.println("Uploaded file Meta: " + fileMeta);
        System.out.println("status:" + fileMeta.getStatus());

        try {
            while (fileMeta.getStatus().equals("processing")) {
                System.out.println("Waiting for video to be processed...");
                TimeUnit.SECONDS.sleep(2);
                fileMeta = service.retrieveFile(fileMeta.getId());
            }
        } catch (Exception e) {
            System.err.println("get file status error：" + e.getMessage());
        }
        System.out.println("Uploaded file Meta: " + fileMeta);

        CreateResponsesRequest request = CreateResponsesRequest.builder()
                .model("doubao-seed-2-0-lite-260215")
                .input(ResponsesInput.builder().addListItem(
                        ItemEasyMessage.builder().role(ResponsesConstants.MESSAGE_ROLE_USER).content(
                                MessageContent.builder()
                                        .addListItem(InputContentItemVideo.builder().fileId(fileMeta.getId()).build())
                                        .addListItem(InputContentItemText.builder().text("请你描述下视频中的人物的一系列动作，以JSON格式输出开始时间（start_time）、结束时间（end_time）、事件（event）、是否危险（danger），请使用HH:mm:ss表示时间戳。").build())
                                        .build()
                        ).build()
                ).build())
                .build();
        ResponseObject resp = service.createResponse(request);
System.out.println(resp);
        service.shutdownExecutor();
    }
}
```



</Tab>
<Tab zoneid="XWQ7mETDw3" title="OpenAI SDK">
<TabTitle>OpenAI SDK</TabTitle>

```Python
import os
import time
from openai import OpenAI

api_key = os.getenv('ARK_API_KEY')

client = OpenAI(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
)

file = client.files.create(
    file=open("/Users/doc/demo.mp4", "rb"),
    purpose="user_data"
)
# Wait for the file to finish processing
while (file.status == "processing"):
    time.sleep(2)
    file = client.files.retrieve(file.id)
print(f"File processed: {file}")
    
response = client.responses.create(
    model="doubao-seed-2-0-lite-260215",
    input=[
        {
            "role": "user",
            "content": [
                {
                    "type": "input_video",
                    "file_id": file.id,
                },
                {
                    "type": "input_text",
                    "text": "请你描述下视频中的人物的一系列动作，以JSON格式输出开始时间（start_time）、结束时间（end_time）、事件（event）、是否危险（danger），请使用HH:mm:ss表示时间戳。",
                },
            ]
        }
    ]
)
print(response)
```



</Tab>
</Tabs>


<span id="22314028"></span>
### Base64 编码传入

将本地文件转换为 Base64 编码字符串，然后提交给大模型。该方式适用于视频文件体积较小的情况，文件不能超过 50 MB，请求体不能超过 64 MB。（Responses API 和 Chat API 都支持该方式。）

<div data-tips="true" data-tips-type="warning" data-tips-is-title="true">注意</div>


<div data-tips="true" data-tips-type="warning">将视频文件转换为Base64编码字符串，然后遵循<code>data:{mime_type};base64,{base64_data}</code>格式拼接，传入模型。</div>



* <div data-tips="true" data-tips-type="warning"><code>{mime_type}</code>：文件的媒体类型，需要与文件格式mime_type对应。支持的视频格式详细见<a href="https://www.volcengine.com/docs/82379/1895586#ea7689ca">视频格式说明</a>。</div>


* <div data-tips="true" data-tips-type="warning"><code>{base64_data}</code>：文件经过Base64编码后的字符串。</div>


* 使用 Responses API 的示例代码如下：



<Tabs>
<Tab zoneid="uYsf1u15VI" title="Curl">
<TabTitle>Curl</TabTitle>

```Bash
BASE64_FILE=$(base64 < demo.mp4) && curl https://ark.cn-beijing.volces.com/api/v3/responses \
   -H "Content-Type: application/json"  \
   -H "Authorization: Bearer $ARK_API_KEY"  \
   -d @- <<EOF
   {
    "model": "doubao-seed-2-0-lite-260215",
    "input": [
      {
        "role": "user",
        "content": [
          {
            "type": "input_video",
            "video_url": "data:video/mp4;base64,$BASE64_FILE",
            "fps": 1
          }
        ]
      }
    ]
  }
EOF
```



</Tab>
<Tab zoneid="Z637lP1bsO" title="Python">
<TabTitle>Python</TabTitle>

```Python
import os
from volcenginesdkarkruntime import Ark
import base64
api_key = os.getenv('ARK_API_KEY')

client = Ark(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
)
# Convert local files to Base64-encoded strings.
def encode_file(file_path):
  with open(file_path, "rb") as read_file:
    return base64.b64encode(read_file.read()).decode('utf-8')
base64_file = encode_file("/Users/doc/demo.mp4")

response = client.responses.create(
    model="doubao-seed-2-0-lite-260215",
    input=[
        {
            "role": "user",
            "content": [
                {    
                    "type": "input_video",
                    "video_url": f"data:video/mp4;base64,{base64_file}",
                    "fps":1
                }
            ],
        }
    ]
)

print(response)
```



</Tab>
<Tab zoneid="XK05l0r2Hl" title="Go">
<TabTitle>Go</TabTitle>

```Go
package main

import (
    "context"
    "encoding/base64"
    "fmt"
    "os"

    "github.com/volcengine/volcengine-go-sdk/service/arkruntime"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime/model/responses"
    "github.com/volcengine/volcengine-go-sdk/volcengine"
)

func main() {
    // Convert local files to Base64-encoded strings.
    fileBytes, err := os.ReadFile("/Users/doc/demo.mp4") 
    if err != nil {
        fmt.Printf("read file error: %v\n", err)
        return
    }
    base64File := base64.StdEncoding.EncodeToString(fileBytes)
    
    client := arkruntime.NewClientWithApiKey(
        os.Getenv("ARK_API_KEY"),
        arkruntime.WithBaseUrl("https://ark.cn-beijing.volces.com/api/v3"),
    )
    ctx := context.Background()

    inputMessage := &responses.ItemInputMessage{
        Role: responses.MessageRole_user,
        Content: []*responses.ContentItem{
            {
                Union: &responses.ContentItem_Video{
                    Video: &responses.ContentItemVideo{
                        Type:     responses.ContentItemType_input_video,
                        VideoUrl: fmt.Sprintf("data:video/mp4;base64,%s", base64File),
                        Fps:      volcengine.Float32(1),
                    },
                },
            },
        },
    }

    resp, err := client.CreateResponses(ctx, &responses.ResponsesRequest{
        Model: "doubao-seed-2-0-lite-260215",
        Input: &responses.ResponsesInput{
            Union: &responses.ResponsesInput_ListValue{
                ListValue: &responses.InputItemList{ListValue: []*responses.InputItem{{
                    Union: &responses.InputItem_InputMessage{
                        InputMessage: inputMessage,
                    },
                }}},
            },
        },
    })
    if err != nil {
        fmt.Printf("response error: %v\n", err)
        return
    }
    fmt.Println(resp)
}
```



</Tab>
<Tab zoneid="fdZE5EQtN8" title="Java">
<TabTitle>Java</TabTitle>

```Java
package com.ark.sample;
import com.volcengine.ark.runtime.model.responses.content.InputContentItemImage;
import com.volcengine.ark.runtime.model.responses.content.InputContentItemText;
import com.volcengine.ark.runtime.model.responses.content.InputContentItemVideo;
import com.volcengine.ark.runtime.model.responses.item.ItemEasyMessage;
import com.volcengine.ark.runtime.service.ArkService;
import com.volcengine.ark.runtime.model.responses.request.*;
import com.volcengine.ark.runtime.model.responses.response.ResponseObject;
import com.volcengine.ark.runtime.model.responses.constant.ResponsesConstants;
import com.volcengine.ark.runtime.model.responses.item.MessageContent;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.Base64;
import java.io.IOException;

public class demo {
    private static String encodeFile(String filePath) throws IOException {
        byte[] fileBytes = Files.readAllBytes(Paths.get(filePath));
        return Base64.getEncoder().encodeToString(fileBytes);
    }
    public static void main(String[] args) {
        String apiKey = System.getenv("ARK_API_KEY");
        ArkService arkService = ArkService.builder().apiKey(apiKey).baseUrl("https://ark.cn-beijing.volces.com/api/v3").build();
        // Convert local files to Base64-encoded strings.
        String base64Data = "";
        try {
            base64Data = "data:video/mp4;base64," + encodeFile("/Users/demo.mp4");
        } catch (IOException e) {
            System.err.println("编码失败: " + e.getMessage());
        }
        CreateResponsesRequest request = CreateResponsesRequest.builder()
                .model("doubao-seed-2-0-lite-260215")
                .input(ResponsesInput.builder().addListItem(
                        ItemEasyMessage.builder().role(ResponsesConstants.MESSAGE_ROLE_USER).content(
                                MessageContent.builder()
                                        .addListItem(InputContentItemVideo.builder().videoUrl(base64Data).fps(2F).build())
                                        .build()
                        ).build()
                ).build())
                .build();
        ResponseObject resp = arkService.createResponse(request);
        System.out.println(resp);

        arkService.shutdownExecutor();
    }
}
```



</Tab>
<Tab zoneid="Fbjx2B99Uw" title="OpenAI SDK">
<TabTitle>OpenAI SDK</TabTitle>

```Python
import os
from openai import OpenAI
import base64

api_key = os.getenv('ARK_API_KEY')

client = OpenAI(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
)
# Convert local files to Base64-encoded strings.
def encode_file(file_path):
  with open(file_path, "rb") as read_file:
    return base64.b64encode(read_file.read()).decode('utf-8')
base64_file = encode_file("/Users/doc/demo.mp4")

response = client.responses.create(
    model="doubao-seed-2-0-lite-260215",
    input=[
        {
            "role": "user",
            "content": [
                {    
                    "type": "input_video",
                    "video_url": f"data:video/mp4;base64,{base64_file}",
                    "fps":1
                }
            ],
        }
    ]
)

print(response)
```



</Tab>
</Tabs>



* 使用 Chat API 的示例代码如下：



<Tabs>
<Tab zoneid="xTecjhtzzG" title="Curl">
<TabTitle>Curl</TabTitle>

```Bash
BASE64_VIDEO=$(base64 < demo.mp4) && curl https://ark.cn-beijing.volces.com/api/v3/chat/completions \
   -H "Content-Type: application/json"  \
   -H "Authorization: Bearer $ARK_API_KEY"  \
   -d @- <<EOF
   {
    "model": "doubao-seed-2-0-lite-260215",
    "messages": [
      {
        "role": "user",
        "content": [
          {
            "type": "video_url",
            "video_url": {
              "url": "data:video/mp4;base64,$BASE64_VIDEO"
            }
          },
          {
            "type": "text",
            "text": "What is in the video?"
          }
        ]
      }
    ],
    "max_tokens": 300
  }
EOF
```



* 按需替换 Model ID，查询 Model ID 参见 [模型列表](https://www.volcengine.com/docs/82379/1330310)。


</Tab>
<Tab zoneid="k2qtdYUl3m" title="Python">
<TabTitle>Python</TabTitle>

```Python
import base64
import os
# Install SDK:  pip install 'volcengine-python-sdk[ark]' .
from volcenginesdkarkruntime import Ark 

client = Ark(
    # The base URL for model invocation .
    base_url="https://ark.cn-beijing.volces.com/api/v3", 
    # Get API Key：https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
    api_key=os.getenv('ARK_API_KEY'), 
)

# 定义方法将指定路径视频转为Base64编码
def encode_video(video_path):
  with open(video_path, "rb") as video_file:
    return base64.b64encode(video_file.read()).decode('utf-8')

# 需传给大模型的视频
video_path = "demo.mp4"

# 将视频转为Base64编码
base64_video = encode_video(video_path)

completion = client.chat.completions.create(
  # Replace with Model ID .
  model = "doubao-seed-2-0-lite-260215",
  messages=[
    {
      "role": "user",
      "content": [
        {
          "type": "video_url",
          "video_url": {
            "url":  f"data:video/<VIDEO_FORMAT>;base64,{base64_video}"
          },         
        },
        {
          "type": "text",
          "text": "What's in the video?",
        },
      ],
    }
  ],
)

print(completion.choices[0])
```



</Tab>
<Tab zoneid="PpjwTMC261" title="Go">
<TabTitle>Go</TabTitle>

```Go
package main

import (
    "context"
    "encoding/base64"
    "fmt"
    "os"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime/model"
    "github.com/volcengine/volcengine-go-sdk/volcengine"
)

func main() {
    // 读取本地视频文件
    videoBytes, err := os.ReadFile("demo.mp4") // 替换为实际视频路径
    if err != nil {
        fmt.Printf("读取视频失败: %v\n", err)
        return
    }
    base64Video := base64.StdEncoding.EncodeToString(videoBytes)

    client := arkruntime.NewClientWithApiKey(
        // Get API Key：https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
        os.Getenv("ARK_API_KEY"),
        // The base URL for model invocation .
        arkruntime.WithBaseUrl("https://ark.cn-beijing.volces.com/api/v3"),
        )
    ctx := context.Background()
    req := model.CreateChatCompletionRequest{
        // Replace with Model ID
        Model: "doubao-seed-2-0-lite-260215",
        Messages: []*model.ChatCompletionMessage{
            {
                Role: "user",
                Content: &model.ChatCompletionMessageContent{
                    ListValue: []*model.ChatCompletionMessageContentPart{
                        {
                            Type: "video_url",
                            VideoURL: &model.ChatMessageVideoURL{
                                URL: fmt.Sprintf("data:video/mp4;base64,%s", base64Video),
                            },
                        },
                        {
                            Type: "text",
                            Text: "What's in the video?",
                        },
                    },
                },
            },
        },
    }

    resp, err := client.CreateChatCompletion(ctx, req)
    if err != nil {
        fmt.Printf("standard chat error: %v\n", err)
        return
    }
    fmt.Println(*resp.Choices[0].Message.Content.StringValue)
}
```



</Tab>
<Tab zoneid="mwxtYdU69o" title="Java">
<TabTitle>Java</TabTitle>

```Java
package com.ark.sample;

import com.volcengine.ark.runtime.model.completion.chat.*;
import com.volcengine.ark.runtime.model.completion.chat.ChatCompletionContentPart.*;
import com.volcengine.ark.runtime.service.ArkService;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;
import okhttp3.ConnectionPool;
import okhttp3.Dispatcher;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Base64;
import java.io.IOException;

public class Sample {
    static String apiKey = System.getenv("ARK_API_KEY");
    static ConnectionPool connectionPool = new ConnectionPool(5, 1, TimeUnit.SECONDS);
    static Dispatcher dispatcher = new Dispatcher();
    static ArkService service = ArkService.builder()
        .dispatcher(dispatcher)
        .connectionPool(connectionPool)
        .baseUrl("https://ark.cn-beijing.volces.com/api/v3") // The base URL for model invocation
        .apiKey(apiKey) //Get API Key：https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
        .build();

    // Base64编码方法
    private static String encodeVideo(String videoPath) throws IOException {
        byte[] videoBytes = Files.readAllBytes(Path.of(videoPath));
        return Base64.getEncoder().encodeToString(videoBytes);
    }

    public static void main(String[] args) throws Exception {

        List<ChatMessage> messagesForReqList = new ArrayList<>();

        // 本地视频路径（替换为实际路径）
        String videoPath = "demo.mp4";

        // 生成Base64数据URL
        String base64Data = "data:video/mp4;base64," + encodeVideo(videoPath);

        // 构建消息内容（修复内容部分构建方式）
        List<ChatCompletionContentPart> contentParts = new ArrayList<>();

        // 图片部分使用builder模式
        contentParts.add(ChatCompletionContentPart.builder()
                .type("video_url")
                .videoUrl(new ChatCompletionContentPartVideoURL(base64Data, 2))
                .build());

        // 文本部分使用builder模式
        contentParts.add(ChatCompletionContentPart.builder()
                .type("text")
                .text("What's in the video?")
                .build());

        // 创建消息
        messagesForReqList.add(ChatMessage.builder()
                .role(ChatMessageRole.USER)
                .multiContent(contentParts)
                .build());

        ChatCompletionRequest req = ChatCompletionRequest.builder()
                .model("doubao-seed-2-0-lite-260215") //Replace with Model ID .
                .messages(messagesForReqList)
                .build();

        service.createChatCompletion(req)
                .getChoices()
                .forEach(choice -> System.out.println(choice.getMessage().getContent()));
        // shutdown service after all requests are finished
        service.shutdownExecutor();
    }
}
```



</Tab>
</Tabs>


<span id="8e3a48ed"></span>
## 视频 URL 传入

如果视频文件已存在公网可访问URL，可以在请求中直接填入视频文件的公网URL，文件不能超过50 MB。（Responses API 和 Chat API 都支持该方式。）


* 使用 Responses API 的示例代码如下：



<Tabs>
<Tab zoneid="v3nuSWB7Bn" title="Curl">
<TabTitle>Curl</TabTitle>

```Bash
curl https://ark.cn-beijing.volces.com/api/v3/responses \
-H "Authorization: Bearer $ARK_API_KEY" \
-H 'Content-Type: application/json' \
-d '{
    "model": "doubao-seed-2-0-lite-260215",
    "input": [
        {
            "role": "user",
            "content": [
                {    
                    "type": "input_video",
                    "video_url": "https://ark-project.tos-cn-beijing.volces.com/doc_video/ark_vlm_video_input.mp4",
                    "fps":1
                }
            ]
        }
    ]
}'
```



</Tab>
<Tab zoneid="eeSrarErSk" title="Python">
<TabTitle>Python</TabTitle>

```Python
import os
from volcenginesdkarkruntime import Ark

# 从环境变量中获取您的API KEY，配置方法见：https://www.volcengine.com/docs/82379/1399008
api_key = os.getenv('ARK_API_KEY')

client = Ark(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
)

response = client.responses.create(
    model="doubao-seed-2-0-lite-260215",
    input=[
        {
            "role": "user",
            "content": [
                {    
                    "type": "input_video",
                    "video_url": "https://ark-project.tos-cn-beijing.volces.com/doc_video/ark_vlm_video_input.mp4",
                    "fps":1
                }
            ],
        }
    ]
)

print(response)
```



</Tab>
<Tab zoneid="kxGuEDV14x" title="Go">
<TabTitle>Go</TabTitle>

```Go
package main

import (
    "context"
    "fmt"
    "os"

    "github.com/volcengine/volcengine-go-sdk/service/arkruntime"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime/model/responses"
    "github.com/volcengine/volcengine-go-sdk/volcengine"
)

func main() {
    client := arkruntime.NewClientWithApiKey(
        //通过 os.Getenv 从环境变量中获取 ARK_API_KEY
        os.Getenv("ARK_API_KEY"),
        arkruntime.WithBaseUrl("https://ark.cn-beijing.volces.com/api/v3"),
    )
    // 创建一个上下文，通常用于传递请求的上下文信息，如超时、取消等
    ctx := context.Background()

    inputMessage := &responses.ItemInputMessage{
        Role: responses.MessageRole_user,
        Content: []*responses.ContentItem{
            {
                Union: &responses.ContentItem_Video{
                    Video: &responses.ContentItemVideo{
                        Type:     responses.ContentItemType_input_video,
                        VideoUrl: "https://ark-project.tos-cn-beijing.volces.com/doc_video/ark_vlm_video_input.mp4",
                        Fps:      volcengine.Float32(1),
                    },
                },
            },
        },
    }

    resp, err := client.CreateResponses(ctx, &responses.ResponsesRequest{
        Model: "doubao-seed-2-0-lite-260215",
        Input: &responses.ResponsesInput{
            Union: &responses.ResponsesInput_ListValue{
                ListValue: &responses.InputItemList{ListValue: []*responses.InputItem{{
                    Union: &responses.InputItem_InputMessage{
                        InputMessage: inputMessage,
                    },
                }}},
            },
        },
    })
    if err != nil {
        fmt.Printf("response error: %v\n", err)
        return
    }
    fmt.Println(resp)
}
```



</Tab>
<Tab zoneid="UHdod6XABm" title="Java">
<TabTitle>Java</TabTitle>

```Java
package com.ark.example;
import com.volcengine.ark.runtime.model.responses.content.InputContentItemImage;
import com.volcengine.ark.runtime.model.responses.content.InputContentItemText;
import com.volcengine.ark.runtime.model.responses.content.InputContentItemVideo;
import com.volcengine.ark.runtime.model.responses.item.ItemEasyMessage;
import com.volcengine.ark.runtime.service.ArkService;
import com.volcengine.ark.runtime.model.responses.request.*;
import com.volcengine.ark.runtime.model.responses.response.ResponseObject;
import com.volcengine.ark.runtime.model.responses.constant.ResponsesConstants;
import com.volcengine.ark.runtime.model.responses.item.MessageContent;


public class demo {
    public static void main(String[] args) {
        String apiKey = System.getenv("ARK_API_KEY");
        // 创建ArkService实例
        ArkService arkService = ArkService.builder().apiKey(apiKey).baseUrl("https://ark.cn-beijing.volces.com/api/v3").build();

        CreateResponsesRequest request = CreateResponsesRequest.builder()
                .model("doubao-seed-2-0-lite-260215")
                .input(ResponsesInput.builder().addListItem(
                        ItemEasyMessage.builder().role(ResponsesConstants.MESSAGE_ROLE_USER).content(
                                MessageContent.builder()
                                        .addListItem(InputContentItemVideo.builder().videoUrl("https://ark-project.tos-cn-beijing.volces.com/doc_video/ark_vlm_video_input.mp4").fps(2F).build())
                                        .build()
                        ).build()
                ).build())
                .build();
        ResponseObject resp = arkService.createResponse(request);
        System.out.println(resp);

        arkService.shutdownExecutor();
    }
}
```



</Tab>
<Tab zoneid="ug8RIxGVvI" title="OpenAI SDK">
<TabTitle>OpenAI SDK</TabTitle>

```Python
import os
from openai import OpenAI

# 从环境变量中获取您的API KEY，配置方法见：https://www.volcengine.com/docs/82379/1399008
api_key = os.getenv('ARK_API_KEY')

client = OpenAI(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
)

response = client.responses.create(
    model="doubao-seed-2-0-lite-260215",
    input=[
        {
            "role": "user",
            "content": [
                {    
                    "type": "input_video",
                    "video_url": "https://ark-project.tos-cn-beijing.volces.com/doc_video/ark_vlm_video_input.mp4",
                    "fps":1
                }
            ],
        }
    ]
)

print(response)
```



</Tab>
</Tabs>



* 使用 Chat API 的示例代码如下：（可参见[控制视频理解的精细度](https://www.volcengine.com/docs/82379/1895586#bf4d9224)）



<Tabs>
<Tab zoneid="oJiUq13iq9" title="Python SDK">
<TabTitle>Python SDK</TabTitle>

```Python
import os
# Install SDK:  pip install 'volcengine-python-sdk[ark]'
from volcenginesdkarkruntime import Ark 

client = Ark(
    # The base URL for model invocation
    base_url="https://ark.cn-beijing.volces.com/api/v3", 
    # Get API Key：https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
    api_key=os.getenv('ARK_API_KEY'), 
)

completion = client.chat.completions.create(
    # Replace with Model ID .
    model = "doubao-seed-2-0-lite-260215",
    messages = [
        {
            "role": "user",  
            "content": [   
                {
                    "type": "video_url",
                    "video_url": {
                        # Replace the link with your actual video link
                        "url":  "https://ark-project.tos-cn-beijing.volces.com/doc_video/ark_vlm_video_input.mp4",
                        "fps": 1
                    }
                },
            ],
        }
    ],
)

print(completion.choices[0].message.content)
```



</Tab>
</Tabs>


<span id="fbc687c2"></span>
# 使用场景

<span id="bf4d9224"></span>
## 控制视频理解的精细度

您可通过 **fps** 字段，控制从视频中抽取图像的频率，默认为1，即每秒从视频中抽取一帧图像，输入给模型进行视觉理解。 可通过 **fps** 字段，控制模型对于视频中图像变化的敏感度。


* 当视频画面变化剧烈或需关注画面变化，如计算视频中角色动作次数，可调高 **fps** 设置（最高 `5`），防止抽帧频率低导致误判。

* 当视频画面变化不频繁或无需关注画面变化，如画面中人数，可调低 **fps** （最低`0.2`），可提升处理速度，节省 token 用量。


示例代码如下：


<Tabs>
<Tab zoneid="Cd4ngzFFME" title="Curl">
<TabTitle>Curl</TabTitle>

```Shell
curl https://ark.cn-beijing.volces.com/api/v3/chat/completions \
   -H "Content-Type: application/json" \
   -H "Authorization: Bearer $ARK_API_KEY" \
   -d '{
    "model": "doubao-seed-2-0-lite-260215",
    "messages": [
        {
            "role": "user",
            "content": [                
                {"type": "video_url","video_url": {"url":  "https://ark-project.tos-cn-beijing.volces.com/doc_video/ark_vlm_video_input.mp4", "fps": 2}},
                {"type": "text", "text": "What is in the video?"}
            ]
        }
    ],
    "max_tokens": 300
  }'
```



* 按需替换 Model ID，查询 Model ID 参见 [模型列表](https://www.volcengine.com/docs/82379/1330310)。


</Tab>
<Tab zoneid="tkBDsYWgME" title="Python">
<TabTitle>Python</TabTitle>

```Python
import os
# Install SDK:  pip install 'volcengine-python-sdk[ark]' .
from volcenginesdkarkruntime import Ark 

client = Ark(
    # The base URL for model invocation .
    base_url="https://ark.cn-beijing.volces.com/api/v3", 
    # Get API Key：https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
    api_key=os.getenv('ARK_API_KEY'), 
)

completion = client.chat.completions.create(
    # Replace with Model ID .
    model = "doubao-seed-2-0-lite-260215",
    messages=[
        {
            # 消息角色为用户
            "role": "user",
            "content": [
                {
                    "type": "video_url",
                    "video_url": {
                        # 替换链接为实际视频链接
                        "url":  "https://ark-project.tos-cn-beijing.volces.com/doc_video/ark_vlm_video_input.mp4",
                        "fps": 2, # 每秒截取2帧画面，用于视频理解
                    }
                },
                # 文本类型的消息内容，询问视频里有什么
                {"type": "text", "text": "What's in the video?"},
            ],
        }
    ],
)

print(completion.choices[0])
```



</Tab>
<Tab zoneid="ZIhNgqacRk" title="Go">
<TabTitle>Go</TabTitle>

```Go
package main

import (
    "context"
    "fmt"
    "os"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime/model"
    "github.com/volcengine/volcengine-go-sdk/volcengine"
)

func main() {
    client := arkruntime.NewClientWithApiKey(
        //Get API Key：https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
        os.Getenv("ARK_API_KEY"),
        // The base URL for model invocation .
        arkruntime.WithBaseUrl("https://ark.cn-beijing.volces.com/api/v3"),
    )
    // 创建一个上下文，通常用于传递请求的上下文信息，如超时、取消等
    ctx := context.Background()
    // 构建消息内容
    contentParts := []*model.ChatCompletionMessageContentPart{
        {
            Type: "video_url",
            VideoURL: &model.ChatMessageVideoURL{
                URL: "https://ark-project.tos-cn-beijing.volces.com/doc_video/ark_vlm_video_input.mp4",
                FPS: volcengine.Float64(2),
            },
        },
        // 文本内容
        {
            Type: "text",
            Text: "What's in the video?",
        },
    }
    // 构建聊天完成请求，设置请求的模型和消息内容
    req := model.CreateChatCompletionRequest{
        // Replace with Model ID
       Model: "doubao-seed-2-0-lite-260215",
       Messages: []*model.ChatCompletionMessage{
          {
             // 消息的角色为用户
             Role: model.ChatMessageRoleUser,
             Content: &model.ChatCompletionMessageContent{
                ListValue: contentParts, // 多类型内容使用ListValue
             },
          },
       },
       MaxTokens: volcengine.Int(300), // 设置模型输出最大 token 数
    }

    // 发送聊天完成请求，并将结果存储在 resp 中，将可能出现的错误存储在 err 中
    resp, err := client.CreateChatCompletion(ctx, req)
    if err!= nil {
       // 若出现错误，打印错误信息并终止程序
       fmt.Printf("standard chat error: %v\n", err)
       return
    }
    // 打印聊天完成请求的响应结果
    fmt.Println(*resp.Choices[0].Message.Content.StringValue)
}
```



</Tab>
<Tab zoneid="mIUGCPHjQk" title="Java">
<TabTitle>Java</TabTitle>

```Java
package com.ark.sample;

import com.volcengine.ark.runtime.model.completion.chat.*;
import com.volcengine.ark.runtime.model.completion.chat.ChatCompletionContentPart.*;
import com.volcengine.ark.runtime.service.ArkService;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;
import okhttp3.ConnectionPool;
import okhttp3.Dispatcher;

public class VideoSample {
  static String apiKey = System.getenv("ARK_API_KEY");
  static ConnectionPool connectionPool = new ConnectionPool(5, 1, TimeUnit.SECONDS);
  static Dispatcher dispatcher = new Dispatcher();
  static ArkService service = ArkService.builder()
      .dispatcher(dispatcher)
      .connectionPool(connectionPool)
      .baseUrl("https://ark.cn-beijing.volces.com/api/v3")  // The base URL for model invocation .
      .apiKey(apiKey) //Get API Key：https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
      .build();

  public static void main(String[] args) throws Exception {

    List<ChatMessage> messagesForReqList = new ArrayList<>();

    // 构建消息内容
    List<ChatCompletionContentPart> contentParts = new ArrayList<>();

    contentParts.add(ChatCompletionContentPart.builder()
        .type("video_url")
        .videoUrl(new ChatCompletionContentPartVideoURL(
            "https://ark-project.tos-cn-beijing.volces.com/doc_video/ark_vlm_video_input.mp4",2))
            
        .build());

    contentParts.add(ChatCompletionContentPart.builder()
        .type("text")
        .text("What's in the video?")
        .build());

    // 创建消息
    messagesForReqList.add(ChatMessage.builder()
        .role(ChatMessageRole.USER)
        .multiContent(contentParts)
        .build());

    ChatCompletionRequest req = ChatCompletionRequest.builder()
        .model("doubao-seed-2-0-lite-260215") //Replace with Model ID .
        .messages(messagesForReqList)
        .maxTokens(300)
        .build();

    service.createChatCompletion(req)
        .getChoices()
        .forEach(choice -> System.out.println(choice.getMessage().getContent()));
    // shutdown service after all requests are finished
    service.shutdownExecutor();
  }
}
```



</Tab>
</Tabs>


<span id="fcee824a"></span>
## 感知视频时序

视频理解可理解视频时间和图像关系信息，如回答事件发生什么时间点，在哪些时间发生了某事件等和时间相关的信息，原理见 [视频理解工作原理](https://www.volcengine.com/docs/82379/1895586#b5f696d3)。

下面是简单示例代码


<Tabs>
<Tab zoneid="glqNGixpnB" title="Curl">
<TabTitle>Curl</TabTitle>

```Shell
curl https://ark.cn-beijing.volces.com/api/v3/chat/completions \
   -H "Content-Type: application/json" \
   -H "Authorization: Bearer $ARK_API_KEY" \
   -d '{
    "model": "doubao-seed-2-0-lite-260215",
    "messages": [
        {
            "role": "user",
            "content": [                
                {"type": "video_url","video_url": {"url":  "https://ark-project.tos-cn-beijing.volces.com/doc_video/video-understanding.mp4", "fps": "5"}},
                {"type": "text", "text": "裁判什么时间点出现的？"}
            ]
        }
    ],
    "max_tokens": 300
  }'
```



* 按需替换 Model ID，查询 Model ID 参见 [模型列表](https://www.volcengine.com/docs/82379/1330310)。


</Tab>
<Tab zoneid="HLAQRvtkNq" title="Python">
<TabTitle>Python</TabTitle>

```Python
import os
# Install SDK:  pip install 'volcengine-python-sdk[ark]' .
from volcenginesdkarkruntime import Ark 

client = Ark(
    # The base URL for model invocation .
    base_url="https://ark.cn-beijing.volces.com/api/v3", 
    # Get API Key：https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
    api_key=os.getenv('ARK_API_KEY'), 
)

completion = client.chat.completions.create(
    # Replace with Model ID .
    model = "doubao-seed-2-0-lite-260215",
    messages=[
        {
            # 消息角色为用户
            "role": "user",
            "content": [
                {
                    "type": "video_url",
                    "video_url": {
                        # 替换链接为实际视频链接
                        "url":  "https://ark-project.tos-cn-beijing.volces.com/doc_video/video-understanding.mp4",
                        "fps": 5, # 每秒截取5帧画面，用于视频理解
                    }
                },
                # 文本类型的消息内容，询问视频里有什么
                {"type": "text", "text": "裁判什么时间点出现的？"},
            ],
        }
    ],
)

print(completion.choices[0])
```



</Tab>
<Tab zoneid="JFjfKDTxTS" title="Go">
<TabTitle>Go</TabTitle>

```Go
package main

import (
    "context"
    "fmt"
    "os"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime/model"
    "github.com/volcengine/volcengine-go-sdk/volcengine"
)

func main() {
    client := arkruntime.NewClientWithApiKey(
        // Get API Key：https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
        os.Getenv("ARK_API_KEY"),
        // The base URL for model invocation .
        arkruntime.WithBaseUrl("https://ark.cn-beijing.volces.com/api/v3"),
    )
    // 创建一个上下文，通常用于传递请求的上下文信息，如超时、取消等
    ctx := context.Background()
    // 构建消息内容
    contentParts := []*model.ChatCompletionMessageContentPart{
        {
            Type: "video_url",
            VideoURL: &model.ChatMessageVideoURL{
                URL: "https://ark-project.tos-cn-beijing.volces.com/doc_video/video-understanding.mp4",
                FPS: volcengine.Float64(5),
            },
        },
        // 文本内容
        {
            Type: "text",
            Text: "裁判什么时间点出现的？",
        },
    }
    // 构建聊天完成请求，设置请求的模型和消息内容
    req := model.CreateChatCompletionRequest{
        // Replace with Model ID
       Model: "doubao-seed-2-0-lite-260215",
       Messages: []*model.ChatCompletionMessage{
          {
             // 消息的角色为用户
             Role: model.ChatMessageRoleUser,
             Content: &model.ChatCompletionMessageContent{
                ListValue: contentParts, // 多类型内容使用ListValue
             },
          },
       },
       MaxTokens: volcengine.Int(300), // 设置模型输出最大 token 数
    }

    // 发送聊天完成请求，并将结果存储在 resp 中，将可能出现的错误存储在 err 中
    resp, err := client.CreateChatCompletion(ctx, req)
    if err!= nil {
       // 若出现错误，打印错误信息并终止程序
       fmt.Printf("standard chat error: %v\n", err)
       return
    }
    // 打印聊天完成请求的响应结果
    fmt.Println(*resp.Choices[0].Message.Content.StringValue)
}
```



</Tab>
<Tab zoneid="eGo48F2cCq" title="Java">
<TabTitle>Java</TabTitle>

```Java
package com.ark.sample;

import com.volcengine.ark.runtime.model.completion.chat.*;
import com.volcengine.ark.runtime.model.completion.chat.ChatCompletionContentPart.*;
import com.volcengine.ark.runtime.service.ArkService;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;
import okhttp3.ConnectionPool;
import okhttp3.Dispatcher;

public class VideoSample {
  static String apiKey = System.getenv("ARK_API_KEY");
  static ConnectionPool connectionPool = new ConnectionPool(5, 1, TimeUnit.SECONDS);
  static Dispatcher dispatcher = new Dispatcher();
  static ArkService service = ArkService.builder()
      .dispatcher(dispatcher)
      .connectionPool(connectionPool)
      .baseUrl("https://ark.cn-beijing.volces.com/api/v3")  // The base URL for model invocation .
      .apiKey(apiKey) //Get API Key：https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
      .build();

  public static void main(String[] args) throws Exception {

    List<ChatMessage> messagesForReqList = new ArrayList<>();

    // 构建消息内容
    List<ChatCompletionContentPart> contentParts = new ArrayList<>();

    contentParts.add(ChatCompletionContentPart.builder()
        .type("video_url")
        .videoUrl(new ChatCompletionContentPartVideoURL(
            "https://ark-project.tos-cn-beijing.volces.com/doc_video/video-understanding.mp4",5))
        .build());

    contentParts.add(ChatCompletionContentPart.builder()
        .type("text")
        .text("裁判什么时间点出现的？")
        .build());

    // 创建消息
    messagesForReqList.add(ChatMessage.builder()
        .role(ChatMessageRole.USER)
        .multiContent(contentParts)
        .build());

    ChatCompletionRequest req = ChatCompletionRequest.builder()
        .model("doubao-seed-2-0-lite-260215") //Replace with Model ID .
        .messages(messagesForReqList)
        .maxTokens(300)
        .build();

    service.createChatCompletion(req)
        .getChoices()
        .forEach(choice -> System.out.println(choice.getMessage().getContent()));
    // shutdown service after all requests are finished
    service.shutdownExecutor();
  }
}
```



</Tab>
</Tabs>


回复预览

```Plain
根据视频描述，裁判在**3.7秒**左右出现。此时，画面中两位拳击手（左为黑T恤红短裤、右为白T恤黑短裤）原本处于对峙状态，随后裁判（穿着黑色西装、戴白手套）站到两人中间，似乎在准备开始比赛或暂停当前回合，观众仍在背景中欢呼。
```


<span id="5cfd1f60"></span>
## 流式输出

流式输出支持内容动态实时呈现，既能够缓解用户等待焦虑，又可以规避复杂任务因长时间推理引发的客户端超时失败问题，保障请求流程顺畅。


<Tabs>
<Tab zoneid="RjsLn68R7E" title="Python SDK">
<TabTitle>Python SDK</TabTitle>

```Python
import asyncio
import os
from volcenginesdkarkruntime import AsyncArk
from volcenginesdkarkruntime.types.responses.response_completed_event import ResponseCompletedEvent
from volcenginesdkarkruntime.types.responses.response_reasoning_summary_text_delta_event import ResponseReasoningSummaryTextDeltaEvent
from volcenginesdkarkruntime.types.responses.response_output_item_added_event import ResponseOutputItemAddedEvent
from volcenginesdkarkruntime.types.responses.response_text_delta_event import ResponseTextDeltaEvent
from volcenginesdkarkruntime.types.responses.response_text_done_event import ResponseTextDoneEvent

client = AsyncArk(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=os.getenv('ARK_API_KEY')
)

async def main():
    # upload video file
    print("Upload video file")
    file = await client.files.create(
        # replace with your local video path
        file=open("/Users/doc/demo.mp4", "rb"),
        purpose="user_data",
        preprocess_configs={
            "video": {
                "fps": 0.3,  # define the sampling fps of the video, default is 1.0
            }
        }
    )
    print(f"File uploaded: {file.id}")

    # Wait for the file to finish processing
    await client.files.wait_for_processing(file.id)
    print(f"File processed: {file.id}")

    stream = await client.responses.create(
        model="doubao-seed-2-0-lite-260215",
        input=[
            {"role": "user", "content": [
                {
                    "type": "input_video",
                    "file_id": file.id  # ref video file id
                },
                {
                    "type": "input_text",
                    "text": "请你描述下视频中的人物的一系列动作，以JSON格式输出开始时间（start_time）、结束时间（end_time）、事件（event）、是否危险（danger），请使用HH:mm:ss表示时间戳。"
                    
                }
            ]},
        ],
        caching={
            "type": "enabled",
        },
        store=True,
        stream=True
    )
    
    async for event in stream:
        if isinstance(event, ResponseReasoningSummaryTextDeltaEvent):
            print(event.delta, end="")
        if isinstance(event, ResponseOutputItemAddedEvent):
            print("\noutPutItem " + event.type + " start:")
        if isinstance(event, ResponseTextDeltaEvent):
            print(event.delta,end="")
        if isinstance(event, ResponseTextDoneEvent):
            print("\noutPutTextDone.")
        if isinstance(event, ResponseCompletedEvent):
            print("Response Completed. Usage = " + event.response.usage.model_dump_json())

if __name__ == "__main__":
    asyncio.run(main())
```



</Tab>
<Tab zoneid="kGeJI2yutW" title="Go SDK">
<TabTitle>Go SDK</TabTitle>

```Go
package main

import (
    "context"
    "fmt"
    "io"
    "os"
    "time"

    "github.com/volcengine/volcengine-go-sdk/service/arkruntime"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime/model/file"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime/model/responses"
    "github.com/volcengine/volcengine-go-sdk/volcengine"
)

func main() {
    client := arkruntime.NewClientWithApiKey(
        // Get API Key：https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
        os.Getenv("ARK_API_KEY"),
        arkruntime.WithBaseUrl("https://ark.cn-beijing.volces.com/api/v3"),
    )
    ctx := context.Background()

    fmt.Println("----- upload video data -----")
    data, err := os.Open("/Users/doc/demo.mp4")
    if err != nil {
        fmt.Printf("read file error: %v\n", err)
        return
    }
    fileInfo, err := client.UploadFile(ctx, &file.UploadFileRequest{
        File:    data,
        Purpose: file.PurposeUserData,
        PreprocessConfigs: &file.PreprocessConfigs{
            Video: &file.Video{
                Fps: volcengine.Float64(0.3),
            },
        },
    })

    if err != nil {
        fmt.Printf("upload file error: %v", err)
        return
    }

    // Wait for the file to finish processing
    for fileInfo.Status == file.StatusProcessing {
        fmt.Println("Waiting for video to be processed...")
        time.Sleep(2 * time.Second)
        fileInfo, err = client.RetrieveFile(ctx, fileInfo.ID) // update file info
        if err != nil {
            fmt.Printf("get file status error: %v", err)
            return
        }
    }
    fmt.Printf("Video processing completed: %s, status: %s\n", fileInfo.ID, fileInfo.Status)
    inputMessage := &responses.ItemInputMessage{
        Role: responses.MessageRole_user,
        Content: []*responses.ContentItem{
            {
                Union: &responses.ContentItem_Video{
                    Video: &responses.ContentItemVideo{
                        Type:   responses.ContentItemType_input_video,
                        FileId: volcengine.String(fileInfo.ID),
                    },
                },
            },
            {
                Union: &responses.ContentItem_Text{
                    Text: &responses.ContentItemText{
                        Type: responses.ContentItemType_input_text,
                        Text: "请你描述下视频中的人物的一系列动作，以JSON格式输出开始时间（start_time）、结束时间（end_time）、事件（event）、是否危险（danger），请使用HH:mm:ss表示时间戳。",
                    },
                },
            },
        },
    }
    createResponsesReq := &responses.ResponsesRequest{
        Model: "doubao-seed-2-0-lite-260215",
        Input: &responses.ResponsesInput{
            Union: &responses.ResponsesInput_ListValue{
                ListValue: &responses.InputItemList{ListValue: []*responses.InputItem{{
                    Union: &responses.InputItem_InputMessage{
                        InputMessage: inputMessage,
                    },
                }}},
            },
        },
        Caching: &responses.ResponsesCaching{Type: responses.CacheType_enabled.Enum()},
    }

    resp, err := client.CreateResponsesStream(ctx, createResponsesReq)
    if err != nil {
        fmt.Printf("stream error: %v\n", err)
        return
    }
    var responseId string
    for {
        event, err := resp.Recv()
        if err == io.EOF {
            break
        }
        if err != nil {
            fmt.Printf("stream error: %v\n", err)
            return
        }
        handleEvent(event)
        if responseEvent := event.GetResponse(); responseEvent != nil {
            responseId = responseEvent.GetResponse().GetId()
            fmt.Printf("Response ID: %s", responseId)
        }
    }
}

func handleEvent(event *responses.Event) {
    switch event.GetEventType() {
    case responses.EventType_response_reasoning_summary_text_delta.String():
        print(event.GetReasoningText().GetDelta())
    case responses.EventType_response_reasoning_summary_text_done.String(): // aggregated reasoning text
        fmt.Printf("\nAggregated reasoning text: %s\n", event.GetReasoningText().GetText())
    case responses.EventType_response_output_text_delta.String():
        print(event.GetText().GetDelta())
    case responses.EventType_response_output_text_done.String(): // aggregated output text
        fmt.Printf("\nAggregated output text: %s\n", event.GetTextDone().GetText())
    default:
        return
    }
}
```



</Tab>
<Tab zoneid="gjdrBjA7h0" title="Java SDK">
<TabTitle>Java SDK</TabTitle>

```Java
package com.ark.example;

import com.volcengine.ark.runtime.model.files.FileMeta;
import com.volcengine.ark.runtime.model.files.PreprocessConfigs;
import com.volcengine.ark.runtime.model.files.UploadFileRequest;
import com.volcengine.ark.runtime.model.files.Video;
import com.volcengine.ark.runtime.service.ArkService;
import com.volcengine.ark.runtime.model.responses.request.*;
import com.volcengine.ark.runtime.model.responses.item.ItemEasyMessage;
import com.volcengine.ark.runtime.model.responses.constant.ResponsesConstants;
import com.volcengine.ark.runtime.model.responses.item.MessageContent;
import com.volcengine.ark.runtime.model.responses.content.InputContentItemVideo;
import com.volcengine.ark.runtime.model.responses.content.InputContentItemText;

import com.volcengine.ark.runtime.model.responses.event.functioncall.FunctionCallArgumentsDoneEvent;
import com.volcengine.ark.runtime.model.responses.event.outputitem.OutputItemAddedEvent;
import com.volcengine.ark.runtime.model.responses.event.outputitem.OutputItemDoneEvent;
import com.volcengine.ark.runtime.model.responses.event.outputtext.OutputTextDeltaEvent;
import com.volcengine.ark.runtime.model.responses.event.outputtext.OutputTextDoneEvent;
import com.volcengine.ark.runtime.model.responses.event.reasoningsummary.ReasoningSummaryTextDeltaEvent;
import com.volcengine.ark.runtime.model.responses.event.response.ResponseCompletedEvent;
import java.io.File;
import java.util.concurrent.TimeUnit;

public class demo {
    public static void main(String[] args) {
        String apiKey = System.getenv("ARK_API_KEY");
        ArkService service = ArkService.builder().apiKey(apiKey).baseUrl("https://ark.cn-beijing.volces.com/api/v3").build();

        System.out.println("===== Upload File Example=====");
        // upload a video for responses
        FileMeta fileMeta;
        fileMeta = service.uploadFile(
                UploadFileRequest.builder().
                        file(new File("/Users/doc/demo.mp4")) // replace with your image file path
                        .purpose("user_data")
                        .preprocessConfigs(PreprocessConfigs.builder().video(new Video(0.3)).build())
                        .build());
        System.out.println("Uploaded file Meta: " + fileMeta);
        System.out.println("status:" + fileMeta.getStatus());

        try {
            while (fileMeta.getStatus().equals("processing")) {
                System.out.println("Waiting for video to be processed...");
                TimeUnit.SECONDS.sleep(2);
                fileMeta = service.retrieveFile(fileMeta.getId());
            }
        } catch (Exception e) {
            System.err.println("get file status error：" + e.getMessage());
        }
        System.out.println("Uploaded file Meta: " + fileMeta);

        CreateResponsesRequest request = CreateResponsesRequest.builder()
                .model("doubao-seed-2-0-lite-260215")
                .stream(true)
                .input(ResponsesInput.builder().addListItem(
                        ItemEasyMessage.builder().role(ResponsesConstants.MESSAGE_ROLE_USER).content(
                                MessageContent.builder()
                                        .addListItem(InputContentItemVideo.builder().fileId(fileMeta.getId()).build())
                                        .addListItem(InputContentItemText.builder().text("请你描述下视频中的人物的一系列动作，以JSON格式输出开始时间（start_time）、结束时间（end_time）、事件（event）、是否危险（danger），请使用HH:mm:ss表示时间戳。").build())
                                        .build()
                        ).build()
                ).build())
                .build();

        service.streamResponse(request)
                .doOnError(Throwable::printStackTrace)
                .blockingForEach(event -> {
                    if (event instanceof ReasoningSummaryTextDeltaEvent) {
                        System.out.print(((ReasoningSummaryTextDeltaEvent) event).getDelta());
                    }
                    if (event instanceof OutputItemAddedEvent) {
                        System.out.println("\nOutputItem " + (((OutputItemAddedEvent) event).getItem().getType()) + " Start: ");
                    }
                    if (event instanceof OutputTextDeltaEvent) {
                        System.out.print(((OutputTextDeltaEvent) event).getDelta());
                    }
                    if (event instanceof OutputTextDoneEvent) {
                        System.out.println("\nOutputText End.");
                    }
                    if (event instanceof OutputItemDoneEvent) {
                        System.out.println("\nOutputItem " + ((OutputItemDoneEvent) event).getItem().getType() + " End.");
                    }
                    if (event instanceof FunctionCallArgumentsDoneEvent) {
                        System.out.println("\nFunctionCall Arguments: " + ((FunctionCallArgumentsDoneEvent) event).getArguments());
                    }
                    if (event instanceof ResponseCompletedEvent) {
                        System.out.println("\nResponse Completed. Usage = " + ((ResponseCompletedEvent) event).getResponse().getUsage());
                    }
                });


        service.shutdownExecutor();
    }
}
```



</Tab>
<Tab zoneid="TZXU68gayI" title="兼容 OpenAI SDK">
<TabTitle>兼容 OpenAI SDK</TabTitle>

```Python
import os
import time
from openai import OpenAI

api_key = os.getenv('ARK_API_KEY')

client = OpenAI(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
)

file = client.files.create(
    file=open("/Users/doc/demo.mp4", "rb"),
    purpose="user_data"
)
# Wait for the file to finish processing
while (file.status == "processing"):
    time.sleep(2)
    file = client.files.retrieve(file.id)
print(f"File processed: {file}")
    
response = client.responses.create(
    model="doubao-seed-2-0-lite-260215",
    input=[
        {
            "role": "user",
            "content": [
                {
                    "type": "input_video",
                    "file_id": file.id,
                },
                {
                    "type": "input_text",
                    "text": "请你描述下视频中的人物的一系列动作，以JSON格式输出开始时间（start_time）、结束时间（end_time）、事件（event）、是否危险（danger），请使用HH:mm:ss表示时间戳。",
                },
            ]
        }
    ],
    stream=True
)


for event in response:
    if event.type == "response.reasoning_summary_text.delta":
        print(event.delta, end="")
    if event.type == "response.output_item.added":
        print("\noutPutItem " + event.type + " start:")
    if event.type == "response.output_text.delta":
        print(event.delta,end="")
    if event.type == "response.output_item.done":
        print("\noutPutTextDone.")
    if event.type == "response.completed":
        print("\nResponse Completed. Usage = " + event.response.usage.model_dump_json())
```



</Tab>
</Tabs>


<span id="c62696a9"></span>
# 使用说明

<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>


<div data-tips="true" data-tips-type="tip">处理完图片/视频后，文件会从方舟服务器删除。方舟不会保留您提交的图片、视频以及文本信息等用户数据来训练模型。</div>


<span id="c203cacb"></span>
## 时序信息

基于 FPS 的抽帧获取视频关键帧，再通过`时间戳+图像`拼接标记时序信息，模型基于该请求中的时序标记和图像内容，实现对视频的完整理解（包括内容变化、动作逻辑、时序关联等）。

详细原理见 [视频理解工作原理](https://www.volcengine.com/docs/82379/1895586#b5f696d3)。

<span id="1d125314"></span>
## 视频格式说明


<span aceTableMode="list" aceTableWidth="1,1,4"></span>
|**视频格式** |**文件扩展名** |**内容格式** **Content Type** |
|---|---|---|
|MP4 |.mp4 |`video/mp4` |
|AVI |.avi |`video/avi` |
|MOV |.mov |* url传入视频：对象存储请设置 Content Type 为`video/quicktime`<br><br>* base64编码：请使用 `video/mov`，即`data:video/mov;base64,<BASE64_ENCODING>` |


> 视频文件格式变种较多，不能保证所有文件都能被识别，请通过测试验证文件能够被正常识别。


<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>



* <div data-tips="true" data-tips-type="tip">常见问题及解决方案参见<a href="https://www.volcengine.com/docs/82379/1359411#85251eec">支持 TS 格式的视频文件吗？</a></div>


* <div data-tips="true" data-tips-type="tip">上传视频至对象存储时设置，详情请参见<a href="https://www.volcengine.com/docs/6349/145523#%E8%AE%BE%E7%BD%AE%E6%96%87%E4%BB%B6%E5%85%83%E6%95%B0%E6%8D%AE">文档</a>。</div>


* <div data-tips="true" data-tips-type="tip">传入 Base64 编码时使用：<a href="https://www.volcengine.com/docs/82379/1895586#f6222fec">Base64 编码输入</a>。</div>


* <div data-tips="true" data-tips-type="tip">视频格式需小写。</div>



<span id="4093d898"></span>
## 视频文件容量

使用 URL 方式传入视频，视频文件不能超过 50MB。

使用 Base64 编码传入视频，视频文件不能超过 50MB，请求体不能超过 64MB。

使用 Files API 上传视频，视频文件不能超过 512 MB。

<span id="ae04f468"></span>
## **支持音频理解**

部分模型支持对视频文件中的音频信息进行理解，详见[视频内嵌音频输入](https://www.volcengine.com/docs/82379/2377589#0a9900d2)。

<span id="203baa92"></span>
## **抽帧策略**

用量说明：单视频最大 token 用量为 80k，单次请求视频最大 token 量还受模型的最大上下文窗口以及最大输入长度（当启用深度思考模式）限制，超出则需调整传入视频数量或视频长度。

基本概念：


* 帧图像：某个时刻的视频画面，本文特指输入给模型的帧图像

* 帧图像张数：视频时长 \* **fps**


方舟会根据帧图像张数，对帧图像进行压缩，以平衡视频的理解精度和 token 用量。

不同模型的抽帧策略不同，具体如下：


|抽帧策略 |doubao\-seed\-1.8 之前的模型 |doubao\-seed\-1.8 模型、doubao\-seed\-2.0 模型 |
|---|---|---|
|单帧最大 tokens |支持 128、160、256、384、512、640 离散 tokens 值。 |* doubao\-seed\-1.8 模型：支持 64、128、192、256、320、384 离散 tokens 值。<br><br>* doubao\-seed\-2.0 模型：支持 tokens 在 [64, 384] 区间内连续动态调整。 |
|单帧对应的max_pixels |单帧最大 tokens \* 28 \* 28<br><br>[10w, 50w] |单帧最大 tokens \* 42 \* 42<br><br>[11w, 67w] |
|抽帧数 |[16帧, 640帧]<br><br>```Bash```<br>```# 最大抽帧数```<br>```80×1024 token ÷ 128 token/帧 = 640 帧```<br> |[16帧, 1280帧]<br><br>```Bash```<br>```# 最大抽帧数```<br>```80×1024 token ÷ 64 token/帧 = 1280 帧```<br> |
|抽帧方案 |<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div><br><br><br><br>* <div data-tips="true" data-tips-type="tip">建议评估输出效果，按需调整fps字段配置或视频时长。</div><br><br><br>* <div data-tips="true" data-tips-type="tip">如果视频二进制数据中未包含帧数编码信息，会按 fps 均匀抽帧。单次请求视频最大 Token 量如果超过模型最大输入长度则会报错；未超过则不报错，但视频输入的 token 可能会超过 80k。</div><br> ||
||* fps 过高或视频长度过长：处理的帧图像数量超出640帧，则按帧图像128tokens，时间间隔`视频时长/640`，均匀抽取640帧。<br><br>* fps 过小或视频长度过短：处理的帧图像数量不足16帧时抽取方案如下：<br><br>   * 视频总帧数 \>= 16帧，均匀抽取16帧。<br><br>   * 视频总帧数 < 16帧，抽取视频所有帧。 |* fps 过高或视频长度过长：处理的帧图像数量超出1280帧，则按帧图像64tokens，时间间隔 `视频时长/1280`，均匀抽取1280帧。<br><br>* fps 过小或视频长度过短：处理的帧图像数量不足16帧时抽取方案如下：<br><br>   * 视频总帧数 \>= 16帧，均匀抽取16帧。<br><br>   * 视频总帧数 < 16帧，抽取视频所有帧。 |


<span id="b5f696d3"></span>
# 视频理解工作原理

视频处理的核心方式为 “帧与时间戳的结构化拼接”，具体规则如下：


* 对视频抽帧得到的每帧图像，在其前插入时间戳文本，格式为 `[<时间戳> second]`。

* 拼接后形成“时间戳+图像”的有序序列，模型通过该序列理解视频的时序逻辑和内容变化。


<span id="245b775b"></span>
## 抽帧逻辑举例


<span aceTableMode="list" aceTableWidth=",,,"></span>
| |FPS 1 |FPS 0.5 |FPS 2 |
|---|---|---|---|
|时间戳 |[0.0 second] |[0.0 second] |[0.0 second] |
|视频帧 |`<IMAGE>` |`<IMAGE>` |`<IMAGE>` |
|时间戳 |[1.0 second] |[2.0 second] |[0.5 second] |
|视频帧 |`<IMAGE>` |`<IMAGE>` |`<IMAGE>` |
|时间戳 |[2.0 second] |[4.0 second] |[1.0 second] |
|视频帧 |`<IMAGE>` |`<IMAGE>` |`<IMAGE>` |
|时间戳 |[3.0 second] | |[1.5 second] |
|视频帧 |`<IMAGE>` | |`<IMAGE>` |
|时间戳 |[4.0 second] | |[2.0 second] |
|视频帧 |`<IMAGE>` | |`<IMAGE>` |
|时间戳 |[5.0 second] | |[2.5 second] |
|视频帧 |`<IMAGE>` | |`<IMAGE>` |
|时间戳 | | |[3.0 second] |
|视频帧 | | |`<IMAGE>` |
|时间戳 | | |[3.5 second] |
|视频帧 | | |`<IMAGE>` |
|时间戳 | | |[4.0 second] |
|视频帧 | | |`<IMAGE>` |
|时间戳 | | |[4.5 second] |
|视频帧 | | |`<IMAGE>` |
|时间戳 | | |[5.0 second] |
|视频帧 | | |`<IMAGE>` |
| |*共6帧* |*共3帧* |*共11帧* |


<span id="8646a93e"></span>
## 多图请求等效

视频理解请求等效于下面示例的多图理解请求。

```Plain
{
    "model": "doubao-seed-2-0-lite-260215",
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type":"text",
                    "text":"你觉得这个恐怖吗？"
                },
                {
                    "type":"text",
                    "text":"[0.0 second]"
                },
                {
                    "type":"image_url",
                    "image_url":{
                        "url":"<image_url_01>"}
                },
                {
                    "type":"text",
                    "text":"[1.0 second]"
                },
                {
                    "type":"image_url",
                    "image_url":{
                        "url":"<image_url_02>"}
                },
                {
                    "type":"text",
                    "text":"[2.0 second]"
                },
                {
                    "type":"image_url",
                    "image_url":{
                        "url":"<image_url_03>"}
                },
                {
                    "type":"text",
                    "text":"[3.0 second]"
                },
                {
                    "type":"image_url",
                    "image_url":{
                        "url":"<image_url_04>"}
                },
                {
                    "type":"text",
                    "text":"[4.0 second]"
                },
                {
                    "type":"image_url",
                    "image_url":{
                        "url":"<image_url_05>"}
                },
                {
                    "type":"text",
                    "text":"[5.0 second]"
                },
                {
                    "type":"image_url",
                    "image_url":{
                        "url":"<image_url_06>"}
                }
            ]
        }
    ]
}
```




