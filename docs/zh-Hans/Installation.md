# Project Babel 2 安装文档

[Project Babel 2](http://github.com/livid/v2ex) 是一个用 [Python](http://www.python.org) 语言写成的运行在 [Google App Engine](http://code.google.com/appengine) 云计算环境中的社区软件，本文详细描述最新版本的 Project Babel 2 的安装过程。

## 在 Google App Engine 注册你的应用

Project Babel 2 需要运行在 Google App Engine 的云计算环境中，因此你首先需要在 [Google App Engine](http://code.google.com/appengine) 网站注册自己的 Application ID。

第一次注册时会需要通过 Google 的手机验证，请填入你的手机号码并加入国家代码即可，比如：

    +8613901012345

通过手机验证之后，即可开始注册自己的 Application ID。Application ID 即网址中 .appspot.com 前面的那串字母及数字，比如在下面的例子中，Application ID 即是 v2ex：

    v2ex.appspot.com

## 使用 git 获取最新源代码

请首先确保系统上安装有 git，Mac OS X 用户可以通过 [MacPorts](http://www.macports.org/) 获得 git：

    sudo port install git-core
    
安装 git 之后，运行以下指令获得最新版本的 Project Babel 2 源代码：

    git clone git://github.com/livid/v2ex.git v2ex
    
之后你需要将获得的那个目录更改为自己的 Application ID。然后将其中的 app.yaml.example 复制为 app.yaml，将其中的 application: 后面的字符串同样更改为自己的 Application ID。

之后，你需要将 config.py.example 复制为 config.py 并做一些必要的修改。比如如果你需要用到 Project Babel 2 内置的 Twitter 客户端，那么你就需要在 config.py 中填入你在 [Twitter](http://twitter.com) 网站上申请的 OAuth Consumer Key 和 Secret。

为了防止恶意注册，Project Babel 2 还使用了 [reCAPTCHA](http://www.google.com/recaptcha)，因此你同样需要在 config.py 填入你自己的 reCAPTCHA 信息。

## 使用 Google App Engine Launcher 进行部署

[Google App Engine Launcher](http://code.google.com/appengine/downloads.html) 是 Google 官方的 App Engine 部署工具，可以非常方便的用于上传和更新自己的 Project Babel 2。该工具需要系统安装有 Python 运行环境，如果你的系统里还没有 Python，Windows 用户建议安装 [ActivePython](http://www.activestate.com/activepython)。

安装好 Google App Engine Launcher 后，选择 Add Existing Application，然后选择之前通过 git 获得的那个目录，然后点击蓝色的 Deploy 按钮，即可完成部署。

第一次部署结束后，将需要等待 Google 完成数据库索引，之后网站才可访问。

## 更多资源

如果你在使用 Project Babel 2 的过程中遇到任何问题，欢迎到官方讨论区探讨：

[http://v2ex.appspot.com/go/babel](http://v2ex.appspot.com/go/babel)