# AutoRepeater
从QQ群的聊天记录中根据关键词选出相似度最高的一句话，通过Word2Vec实现

## Usage

### 预处理
导出txt格式的群聊记录，并拼接成一个文件放在./dataset/raw.txt中
然后执行`python word2vector/read_data.py`
可以得到筛选过后的聊天记录文件target.txt

### 训练
`python word2vector/word2vector.py`
模型会保存在model文件夹中

### 使用
运行`python app.py`即可

### 测试
用postman给localhost:7777/message发送一个post请求
form为以下几个参数：
- msg：需要预测的句子
- group: 群号
- qq：qq号