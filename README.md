# skyland-auto-sign

明日方舟、明日方舟：终末地的森空岛签到脚本，支持本地、GitHub Actions、Docker/NAS 与华为云 FunctionGraph。

有四种方法部署
> 1.自己手动在电脑上运行（不想挂载在服务器上的用户推荐这个，因为可以配合MAA一键签到）
>
> 2.在云函数上部署（推荐，省时省力，不用装环境，几乎不用管）
>
> 3.使用Github Actions托管（相比云函数来讲非常推荐，因为有日志会存储，而且也免费）
>
> 4.使用家用NAS面板部署
>

## 快速导航

- [在自己电脑上运行](#mode1)
    - [配合MAA运行](#maa)
- [在云函数上运行](#mode2)
  - [使用手机进行操作](#mobile)
- [使用Github Actions托管](#mode3)
- [使用家用NAS](#mode4)
- [多账号支持](#multiple_account)
- [多端登录问题](#multiple_login)
- [有关新版本参数验证](#sign-headers)
- [有关新版本获得Cred必传的dId参数](#dId)

[视频用法]( https://www.bilibili.com/video/BV1DP411h7s6)

<a name="mode1"></a>

## 方法1

1.安装 Python 3.11 或以上版本。

2.克隆源代码，并在仓库根目录执行 `python -m pip install -r requirements.txt` 安装固定版本依赖。

3.命令提示符运行`python src/main.py`（结果输出如下就代表你成功了）
![img.png](assets/img_0.png)

（以上3步可以用我打好的exe文件直接运行，链接见[release](https://gitee.com/FancyCabbage/skyland-auto-sign/releases)

4.本软件有3种模式：

第一个模式和第二个模式不多说了，填入你的信息即可。

就是注意一下输入的密码是不会显示的，但实际是有的，这点需要注意一下！

如果第一种模式和第二种模式你都没法过人机验证的话，可以使用第三种模式：

登录电脑的森空岛[官网](https://www.skland.com/)
![img.png](assets/img.png)

登录完成后，访问[这个网址](https://web-api.skland.com/account/info/hg) 。然后复制这里的所有内容，粘贴进去即可。
![img_1.png](assets/img_1.png)
![img_2.png](assets/img_2.png)

最后再次启动的时候，脚本就不会再询问你是否添加账号了，而是直接帮你签到了

1.3版本在脚本路径下多了一个`添加账号.bat`,双击运行会再次出现登陆界面，按照步骤走可以再次添加一个账号
<a name="maa"></a>

### MAA支持

可以使用MAA自动执行脚本

MAA在连接设置里有运行前脚本，输入`main.py`的路径后，每次连接模拟器时会自动帮你签到。

如果你用的exe版本的，请输入`main.exe`的路径！
![img_3.png](assets/img_3.png)

第一次执行的话应该还是会出现这个东西
![img_4.png](assets/img_4.png)

设置完毕后直接应该会执行完成，以后都会这样
![img_5.png](assets/img_5.png)

TOKEN和日志应该都会被存储在MAA根路径下
![img_6.png](assets/img_6.png)

<a name="mode2"></a>

## 方法2

使用华为云 FunctionGraph 托管定时签到。下面沿用原说明的“创建函数 → 上传代码 → 添加账号 → 测试 → 配置定时器”流程，补上当前版本需要填写的参数。

本仓库已提供 [cloud_functions/cloud_functions.zip](cloud_functions/cloud_functions.zip)，下载现成包无需启用 GitHub Actions，也无需在自己电脑上安装 Python 或编译。当前包适用于 **Linux x86_64、glibc 2.28 及以上的兼容环境**。

> 以下配图沿用原说明中的旧版控制台截图，仅供定位操作入口。运行时、文件结构、账号配置和 Cron 表达式请按本节文字填写；控制台界面可能随版本调整。

### 1. 登录华为云并进入 FunctionGraph

先注册并登录华为云账号，按控制台提示完成必要的账号验证，然后进入 [函数工作流 FunctionGraph 控制台](https://console.huaweicloud.com/functiongraph)。选择准备部署的区域，在左侧找到“函数 → 函数列表”。

### 2. 创建一个空白函数

在函数列表页面点击“创建函数”，选择创建空白函数。

![旧版控制台的创建函数入口](assets/img_8.png)

### 3. 选择事件函数和定制运行时

按照下面的表格填写创建页面；名称可以自行修改，例如 `skyland-auto-sign`。

| 配置项 | 填写方式 |
| --- | --- |
| 函数类型 | **事件函数** |
| 区域 / 项目 | 选择自己的部署区域和项目 |
| 函数名称 | 例如 `skyland-auto-sign` |
| 运行时 | **定制运行时** |
| CPU 架构 | 如页面提供架构选项，选择与部署包一致的 **x86_64** |

这个 ZIP 自带 Python 和依赖，由根目录的 `bootstrap` 启动。运行时选择“定制运行时”，不需要为该包另选内置 Python 版本或填写 `src/main.py` 作为入口。其余必填项按控制台提示完成后，创建函数。

![旧版控制台选择事件函数和定制运行时](assets/img_9.png)

### 4. 下载已经构建好的部署包

打开仓库中的 [cloud_functions.zip 文件](cloud_functions/cloud_functions.zip) 并下载，也可以使用 [直接下载链接](https://raw.githubusercontent.com/angel12538/skyland-auto-sign2/main/cloud_functions/cloud_functions.zip)。文件约 18 MB。

需要上传的是这个单独的 `cloud_functions.zip`，不是 GitHub“Download ZIP”下载的整个源码仓库。直接保留下载文件即可，无需先解压、重新压缩；包内的账号文件默认是空的。

本目录还提供 [SHA256 校验值](cloud_functions/cloud_functions.zip.sha256) 和 [构建来源信息](cloud_functions/PACKAGE_INFO.json)，需要时可核对。

### 5. 上传 ZIP 并部署代码

进入刚创建的函数详情页，在“代码”页签找到“上传自 → ZIP 文件”或对应的代码上传入口，选择下载的 `cloud_functions.zip`。上传后，按控制台提示保存并部署。

![旧版控制台上传 ZIP 的入口](assets/img_10.png)

上传的 ZIP 解开后，根目录应直接包含以下内容：

```text
bootstrap
index/index
index/_internal/...
INPUT_HYPERGRYPH_TOKEN.txt
BUILD_INFO.json
```

`bootstrap` 必须位于 ZIP 根目录并保留可执行权限，不能在外面再套一层 `cloud_functions` 文件夹。仓库提供的包已处理好目录和权限，相关要求见 [华为云定制运行时说明](https://support.huaweicloud.com/intl/zh-cn/devg-functiongraph/functiongraph_01_0406.html)。

### 6. 配置账号 TOKEN（推荐使用环境变量）

在函数详情页进入“设置 → 常规设置”，找到“环境变量”，点击编辑或添加环境变量。

| 变量名 | 变量值 | 说明 |
| --- | --- | --- |
| `TOKEN` | 你的鹰角网络通行证 Token | 必填，账号获取方式见上面的“方法1” |
| `TZ` | `Asia/Shanghai` | 建议填写，用于程序的本地日期和时间 |

获取账号时，可以登录森空岛官网，再访问 [账号信息接口](https://web-api.skland.com/account/info/hg)，将返回 JSON 中 `data.content` 的字符串填入 `TOKEN`。当前程序也支持直接填写完整的账号 JSON。

多个账号可以在同一个 `TOKEN` 变量中用英文逗号分隔，例如下面的写法；请把示例文字换成自己的值：

```text
第一个账号的Token,第二个账号的Token
```

填写后点击保存。账号和推送密钥在自己的云函数中配置，不要填回公开仓库的文件。

### 7. 如果想沿用原说明的账号文件方式

也可以在函数“代码”页面打开根目录的 `INPUT_HYPERGRYPH_TOKEN.txt`，每行填入一个账号 Token，再保存并部署。原说明的填写方式如下图，当前代码目录以上传包的实际内容为准。

![原说明中账号文件逐行填写的示例](assets/img_13.png)

使用文件时，**删除函数环境变量里的 `TOKEN` 项**，不要只把值留空：只要存在这个变量，程序就会优先读取它。默认会从云函数代码根目录读取上述文件，通常不需要额外设置 `TOKEN_FILE`；使用自定义位置时，可通过 `TOKEN_FILE` 指定文件的绝对路径。

### 8. 配置推送通知（可选）

仍在函数的“环境变量”中，按需要添加对应渠道的密钥；不使用的渠道不用填写。

| 变量名 | 对应渠道 | 填写内容 |
| --- | --- | --- |
| `SC3_SENDKEY` | Server酱³ / Server酱 Turbo | 自己的 SendKey，程序会按密钥类型选择接口 |
| `PUSHPLUS_TOKEN` | PushPlus | 自己的推送 Token |
| `QMSG_TOKEN` | Qmsg | 自己的推送密钥 |

使用 Server酱³ 时，先在 [Server酱³ 官网](https://sc3.ft07.com/) 注册并获取 SendKey，在手机上安装并登录对应 App，再把 SendKey 填入 `SC3_SENDKEY`。

默认会记录推送失败，但只把签到失败视为函数执行失败。若希望推送请求失败时函数也报错，可以再添加 `EXIT_WHEN_PUSH_FAIL=on`。保存环境变量后，再执行测试确认通知情况。

### 9. 调整执行超时并检查网络

在“设置 → 常规设置”中，可以先将执行超时设为 **180 秒**、内存设为 **256 MB** 作为初次测试的起点，再根据实际运行耗时和内存使用情况调整。账号、角色或推送渠道较多时，需要相应增加执行超时。

程序需要访问公网中的森空岛、设备 ID 服务及所用推送服务。如果绑定了 VPC 或自定义网络，要确保该网络具备相应的公网出网能力。

注意，控制台前端的等待提醒与函数实际执行超时是两回事：官方说明前端等待超过 90 秒可能提示超时，而后台仍在运行。遇到这种情况先查看运行日志，再判断是否重试。设置项及限制见 [华为云常规信息配置说明](https://support.huaweicloud.com/intl/zh-cn/usermanual-functiongraph/functiongraph_01_1828.html)。

### 10. 保存部署并手动测试一次

确认代码和环境变量都已保存，代码处于已部署状态，然后点击“测试”。首次测试时创建一个测试事件，例如命名为 `manual-test`，事件内容填写：

```json
{}
```

程序会从环境变量或账号文件读取账号，测试事件中不需要填写 Token。创建事件后执行测试。

![旧版控制台创建测试事件的入口](assets/img_14.png)

当前版本的正常返回结果类似下面这样，具体角色和奖励以实际输出为准：

```json
{
  "success": true,
  "push_success": true,
  "logs": [
    "[明日方舟]角色示例角色(官服)签到成功，获得了龙门币×500"
  ]
}
```

`success` 表示所有已处理账号 / 角色的签到结果；明确的“今日已签到”响应也按成功处理。`push_success` 表示已启用推送渠道的请求是否被服务端接受；没有配置推送渠道时，该值也为 `true`，实际送达仍需在手机端确认。

如果某个账号签到失败，程序会保留其他账号和已完成角色的结果，并向华为云上报失败。先查看返回的 `logs` 或“监控 → 日志”中的错误原因，手动测试通过后再配置定时任务。

### 11. 添加每天自动执行的定时触发器

在函数详情页找到“创建触发器”或“添加触发器”，选择“定时触发器（TIMER）”。

![旧版控制台创建触发器的入口](assets/img_16.png)

![旧版控制台选择 TIMER 触发器](assets/img_17.png)

定时器名称可以填 `skyland-daily`，触发规则选择“Cron 表达式”。沿用原说明“每天北京时间凌晨 1 点 01 分执行”的例子，填写：

```text
CRON_TZ=Asia/Shanghai 0 1 1 * * *
```

其中 `CRON_TZ=Asia/Shanghai` 明确指定北京时间；后面六个字段依次是“秒、分、时、日、月、星期”。如果希望每天北京时间 08:15 执行，可以改为：

```text
CRON_TZ=Asia/Shanghai 0 15 8 * * *
```

官方说明未设置 `CRON_TZ` 时默认使用区域所在时区，因此这里显式指定时区。函数环境变量中的 `TZ` 只影响程序本地时间，不会替代触发器的时区配置。规则依据见 [华为云 TIMER 触发器说明](https://support.huaweicloud.com/usermanual-functiongraph/functiongraph_01_0207.html)。

![旧版控制台填写 Cron 的位置，具体表达式按上文填写](assets/img_18.png)

“是否开启”保持启用；“附加信息”可以留空。确认触发器绑定的是刚刚测试通过的函数版本或别名，然后保存。GitHub Actions 的定时设置不会应用到华为云函数。

### 12. 查看后续运行结果和处理常见问题

到下一次触发时间后，在函数的“监控 → 日志”中查看执行结果；配置了推送时，同时检查手机通知。若控制台要求先开启日志记录功能，按页面提示配置后再查询。

| 现象 | 优先检查 |
| --- | --- |
| 提示“没有可用账号” | `TOKEN` 是否已保存；使用文件时是否已删除 `TOKEN` 环境变量，文件名及内容是否正确 |
| 提示认证失败或“用户未登录” | 重新获取鹰角网络通行证，更新云函数中的账号配置 |
| 启动失败、找不到 `bootstrap` 或架构 / glibc 报错 | 是否上传了正确的部署 ZIP、是否选了事件函数和定制运行时，以及运行环境是否兼容 x86_64 / glibc 2.28 基线 |
| 请求失败、设备 ID 获取失败或执行超时 | 公网出网能力、服务是否暂时不可用，以及函数的执行超时设置 |
| 签到正常但没有收到推送 | 对应推送密钥、`push_success` 与日志中的渠道错误，以及手机端实际接收情况 |
| 没有按时执行 | 触发器是否已启用、绑定版本是否正确，以及 Cron 中的时区和时间 |

以后更新程序时，重新上传新的部署 ZIP 并部署，再手动测试一次。修改源码后需要重新构建部署包；Linux 手动打包可参考 [构建脚本](.build/build_cloud_function.sh) 和 [构建依赖](requirements-build.txt)，版本来源及校验值见 [PACKAGE_INFO.json](cloud_functions/PACKAGE_INFO.json) 与 [SHA256 校验文件](cloud_functions/cloud_functions.zip.sha256)。

仓库提供的包已通过 Linux 构建和离线检查，实际账号签到与具体云端环境仍以部署后的测试结果为准。

<a name="mobile"></a>

## 方法3

使用Github Action自动运行脚本

本方法需要你有一定的git使用经验

首先确认自己的github处于登录状态，然后自己新建一个仓库

将本仓库的源代码全部下载下来，上传到github

进入自己仓库的项目主页后，在上方的菜单中进入Settings > Secrets and variables > Actions

点击 New repository secret


 **创建名为`TOKEN`的环境变量（注意变量名全大写），并填入你的鹰角网络通行证，如果要管理多个账号，换行即可** 

 **如果要开启 Server酱³ APP 推送的话，就创建名为 `SC3_SENDKEY` 的环境变量；如果是第一次使用 Server酱³ 的话，需要到 [Server酱³ 官网](https://sc3.ft07.com/) 注册一个账号，再在手机上下载 Server酱³ App。**

`SC3_SENDKEY`: Server酱³ SendKey（形如 sctp12345tXXXX...）


如果是第一次使用GitHub Action的话，还需要手动打开这个功能 在你仓库上方菜单中进入Actions

点击 I understand... enable them > Enable workflow

之后就可以自动运行签到了, 想要手动测试的话，选择左侧的Auto Sign > Run workflow, 刷新页面就能看到结果了

签到失败默认返回非零退出码，工作流会标记为失败；可设置 Variable `EXIT_WHEN_FAIL=off` 关闭这一退出策略。推送失败默认记录错误，设置 `EXIT_WHEN_PUSH_FAIL=on` 后也会使工作流失败。GitHub 邮件通知仍取决于账号的 Actions 通知设置。

还支持 `PUSHPLUS_TOKEN`、`QMSG_TOKEN` 两个可选 Secret。推送检查渠道业务返回值；“请求被服务端接受”不等于通知最终送达。

<a name="mode4"></a>

## 使用NAS部署

其实和Github Action的配置方式一样，导入脚本以后， **创建一个`TOKEN`的环境变量** 即可。

 **如果要开启 Server酱³ APP 推送的话，就创建名为 `SC3_SENDKEY` 的环境变量。如果是第一次使用 Server酱³ 的话，需要到 [Server酱³ 官网](https://sc3.ft07.com/) 注册一个账号，再在手机上下载 Server酱³ App。** 

`SC3_SENDKEY`: Server酱³ SendKey（形如 sctp12345tXXXX...）。


每个面板可能创建方式不太一样，不展示了

Docker 可通过 `docker build -t skyland-auto-sign .` 构建，再使用 `docker run --rm --env-file .env skyland-auto-sign` 运行。在本地 `.env` 中设置 `TOKEN` 及所需推送密钥；该文件、账号文件、实际推送配置和日志均被构建排除，镜像中不包含它们。容器以普通用户运行。

本地推送配置也可将 `src/push/config.example.ini` 复制为 `src/push/config.ini` 后填写。实际配置文件已被 Git 和 Docker 忽略；环境变量优先于文件，旧拼写 `PUSHPLUSH_TOKEN` 会兼容并提示改名。

网络请求默认连接/读取超时为 5/20 秒，不会自动重试签到 POST。使用代理时设置 `USE_PROXY=on`，可用 `PROXY_URL` 指定地址；`off`、`false`、`0` 均会关闭这个显式代理开关。系统标准代理环境变量仍按 Requests 规则生效。HTTPS 始终校验证书，私有 CA 可通过 `REQUESTS_CA_BUNDLE` 配置。

<a name="multiple_account"></a>

## 多账号支持

普通 Token 支持换行或英文逗号分隔，解析后去重；也支持官网返回的完整账号 JSON、每行一个账号 JSON 或 JSON 数组。文件配置可用 `TOKEN_FILE` 指定路径。无账号的后台任务会明确失败，不进入交互提示。

每个角色和账号独立处理：一个角色失败不会跳过后续角色，已完成结果会保留。认证失效只报告当前账号的问题，不会删除保存其他账号的文件。明确的已签到响应按成功处理，未知非零业务码按失败处理。

## 开发检查

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s test -v
python -m pip check
```

测试禁止真实游戏和推送请求，覆盖失败状态、凭据保留、多账号解析、代理证书校验、日志脱敏、推送业务错误与云函数入口。`Checks` 工作流另外验证 Linux 部署包和 Docker 镜像不会携带本地凭据。

### 使用浏览器登录多个账号获得TOKEN时要注意的问题

**不要去登出账号，否则鹰角网络通行证会失效！**

如果要添加多个账号，请删除浏览器缓存。或者使用浏览器自带的隐私浏览模式，拿到Token后，关闭隐私窗口，再登录一次即可！
![img_20.png](assets/img_20.png)
![img_21.png](assets/img_21.png)

<a name="multiple_account"></a>

## 多端登录的问题

同一账号多端登录是没问题的，但是要注意一点就是电脑在用密码登录后，手机客户端有可能会被挤掉

最后就是别手贱去点客户端里的清理会话，因为那样子会把所有的登录状态清空

## sign-header

新版本森空岛添加了参数验证，有两个方法可以绕过，推荐第一种方法

1.森空岛签名请求头算法：

接口地址（不包括网址） + 如果是GET则使用网址问号后面的参数。如果是POST则使用body的json的字符串 + 时间戳 +
请求头的四个重要参数(`platform`,`timestamp`,`dId`和`vName`).toJSON()

将此字符串做HMAC加密，算法为SHA-256，密钥为请求cred接口会返回的一个token

再将加密后的字符串做MD5即得到签名

例子：

```text
    
    拼接的字符串：
    /api/v1/game/player/binding1695184599{"platform":"","timestamp":"1695184599","dId":"","vName":""}
    将其做hmac-sha256
    6b0516d1325dea1207e03f6840cd0c15ef2f55959c3d0ed2f18d99102a9cc7f5
    再做md5
    92229bf3c18c476e77bcd70c2bd997d3
    最后就是sign的头了
    
```

注意：

请求头四个值`platform`,`timestamp`,`dId`和`vName`必传，然后注意一下字符串顺序，四个值必须按照这样的顺序拼接

其中`platform`,`dId`和`vName`里面的值随便填

`timestamp`为时间戳，以秒为单位
不过`timestamp`因为精度问题容易造成服务器响应`请勿修改设备时间`，此时把这个时间戳稍微减少几秒就行


2.使用旧版本森空岛请求头，防止验参

```text
'User-Agent': 'Skland/1.0.1 (com.hypergryph.skland; build': '100001014; Android 31; ) Okhttp/4.11.0',
'vCode': '100001014',
'vName': '1.0.1',
'dId': 'de9759a5afaa634f',
'platform': '1'
```

<a name="dId"></a>
## 有关新版本获得Cred必传的dId参数

2024.9.10 森空岛登入接口引入了数美接口，请求头必须传递dId参数，导致无法正常登陆

现已解决，具体实现看`SecuritySm.py`文件
