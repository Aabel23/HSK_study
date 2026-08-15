"""Idempotently seed the SQLite database with the classic 150-word HSK1 set."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import get_connection, initialize_database, utc_now
from scripts.meaning_quality import is_english_gloss, repair_mojibake


# hanzi, pinyin, meaning, example, example_pinyin, example_meaning, topic
HSK1_VOCABULARY = [
    ("爱", "ài", "yêu", "我爱妈妈。", "Wǒ ài māma.", "Tôi yêu mẹ.", "Con người"),
    ("八", "bā", "tám", "我有八本书。", "Wǒ yǒu bā běn shū.", "Tôi có tám quyển sách.", "Con số"),
    ("爸爸", "bàba", "bố, ba", "我爸爸是医生。", "Wǒ bàba shì yīshēng.", "Bố tôi là bác sĩ.", "Gia đình"),
    ("杯子", "bēizi", "cái cốc", "杯子里有水。", "Bēizi lǐ yǒu shuǐ.", "Trong cốc có nước.", "Đồ vật"),
    ("北京", "Běijīng", "Bắc Kinh", "我住在北京。", "Wǒ zhù zài Běijīng.", "Tôi sống ở Bắc Kinh.", "Địa điểm"),
    ("本", "běn", "quyển (lượng từ)", "这是一本汉语书。", "Zhè shì yì běn Hànyǔ shū.", "Đây là một quyển sách tiếng Trung.", "Đồ vật"),
    ("不", "bù", "không", "我不喝茶。", "Wǒ bù hē chá.", "Tôi không uống trà.", "Đại từ"),
    ("不客气", "bú kèqi", "không có gì", "不客气，再见！", "Bú kèqi, zàijiàn!", "Không có gì, tạm biệt!", "Chào hỏi"),
    ("菜", "cài", "món ăn, rau", "这个菜很好吃。", "Zhège cài hěn hǎochī.", "Món này rất ngon.", "Ăn uống"),
    ("茶", "chá", "trà", "请喝茶。", "Qǐng hē chá.", "Mời uống trà.", "Ăn uống"),
    ("吃", "chī", "ăn", "我想吃米饭。", "Wǒ xiǎng chī mǐfàn.", "Tôi muốn ăn cơm.", "Ăn uống"),
    ("出租车", "chūzūchē", "xe taxi", "我们坐出租车去。", "Wǒmen zuò chūzūchē qù.", "Chúng tôi đi bằng taxi.", "Địa điểm"),
    ("打电话", "dǎ diànhuà", "gọi điện thoại", "我给妈妈打电话。", "Wǒ gěi māma dǎ diànhuà.", "Tôi gọi điện cho mẹ.", "Hoạt động"),
    ("大", "dà", "to, lớn", "这个苹果很大。", "Zhège píngguǒ hěn dà.", "Quả táo này rất to.", "Tính chất"),
    ("的", "de", "của; trợ từ sở hữu", "这是我的书。", "Zhè shì wǒ de shū.", "Đây là sách của tôi.", "Đại từ"),
    ("点", "diǎn", "giờ; điểm", "现在三点。", "Xiànzài sān diǎn.", "Bây giờ là ba giờ.", "Thời gian"),
    ("电脑", "diànnǎo", "máy tính", "我用电脑学习。", "Wǒ yòng diànnǎo xuéxí.", "Tôi dùng máy tính để học.", "Đồ vật"),
    ("电视", "diànshì", "tivi", "爸爸在看电视。", "Bàba zài kàn diànshì.", "Bố đang xem tivi.", "Đồ vật"),
    ("电影", "diànyǐng", "phim", "我们去看电影。", "Wǒmen qù kàn diànyǐng.", "Chúng ta đi xem phim.", "Hoạt động"),
    ("东西", "dōngxi", "đồ vật, thứ", "我买了一些东西。", "Wǒ mǎi le yìxiē dōngxi.", "Tôi đã mua vài thứ.", "Đồ vật"),
    ("都", "dōu", "đều", "我们都是学生。", "Wǒmen dōu shì xuésheng.", "Chúng tôi đều là học sinh.", "Đại từ"),
    ("读", "dú", "đọc", "她在读书。", "Tā zài dú shū.", "Cô ấy đang đọc sách.", "Hoạt động"),
    ("对不起", "duìbuqǐ", "xin lỗi", "对不起，我来晚了。", "Duìbuqǐ, wǒ lái wǎn le.", "Xin lỗi, tôi đến muộn.", "Chào hỏi"),
    ("多", "duō", "nhiều", "这里人很多。", "Zhèlǐ rén hěn duō.", "Ở đây có rất nhiều người.", "Tính chất"),
    ("多少", "duōshao", "bao nhiêu", "这个多少钱？", "Zhège duōshao qián?", "Cái này bao nhiêu tiền?", "Câu hỏi"),
    ("儿子", "érzi", "con trai", "他有一个儿子。", "Tā yǒu yí ge érzi.", "Ông ấy có một con trai.", "Gia đình"),
    ("二", "èr", "hai", "今天是二号。", "Jīntiān shì èr hào.", "Hôm nay là ngày mùng hai.", "Con số"),
    ("饭店", "fàndiàn", "nhà hàng", "饭店在前面。", "Fàndiàn zài qiánmiàn.", "Nhà hàng ở phía trước.", "Địa điểm"),
    ("飞机", "fēijī", "máy bay", "他坐飞机去北京。", "Tā zuò fēijī qù Běijīng.", "Anh ấy đi máy bay đến Bắc Kinh.", "Địa điểm"),
    ("分钟", "fēnzhōng", "phút", "请等十分钟。", "Qǐng děng shí fēnzhōng.", "Vui lòng đợi mười phút.", "Thời gian"),
    ("高兴", "gāoxìng", "vui vẻ", "认识你很高兴。", "Rènshi nǐ hěn gāoxìng.", "Rất vui được biết bạn.", "Tính chất"),
    ("个", "gè", "cái, người (lượng từ)", "我有一个朋友。", "Wǒ yǒu yí ge péngyou.", "Tôi có một người bạn.", "Con số"),
    ("工作", "gōngzuò", "làm việc, công việc", "我爸爸在医院工作。", "Wǒ bàba zài yīyuàn gōngzuò.", "Bố tôi làm việc ở bệnh viện.", "Công việc"),
    ("狗", "gǒu", "con chó", "那只狗很小。", "Nà zhī gǒu hěn xiǎo.", "Con chó kia rất nhỏ.", "Đồ vật"),
    ("汉语", "Hànyǔ", "tiếng Trung", "我学习汉语。", "Wǒ xuéxí Hànyǔ.", "Tôi học tiếng Trung.", "Trường học"),
    ("好", "hǎo", "tốt, khỏe", "今天天气很好。", "Jīntiān tiānqì hěn hǎo.", "Hôm nay thời tiết rất đẹp.", "Tính chất"),
    ("号", "hào", "ngày; số", "今天是五号。", "Jīntiān shì wǔ hào.", "Hôm nay là ngày mùng năm.", "Ngày tháng"),
    ("喝", "hē", "uống", "你喝水吗？", "Nǐ hē shuǐ ma?", "Bạn uống nước không?", "Ăn uống"),
    ("和", "hé", "và", "我和她都是学生。", "Wǒ hé tā dōu shì xuésheng.", "Tôi và cô ấy đều là học sinh.", "Đại từ"),
    ("很", "hěn", "rất", "她很漂亮。", "Tā hěn piàoliang.", "Cô ấy rất xinh đẹp.", "Tính chất"),
    ("后面", "hòumiàn", "phía sau", "学校后面有商店。", "Xuéxiào hòumiàn yǒu shāngdiàn.", "Phía sau trường có cửa hàng.", "Địa điểm"),
    ("回", "huí", "trở về", "我下午回家。", "Wǒ xiàwǔ huí jiā.", "Buổi chiều tôi về nhà.", "Hoạt động"),
    ("会", "huì", "biết, có thể", "我会说汉语。", "Wǒ huì shuō Hànyǔ.", "Tôi biết nói tiếng Trung.", "Hoạt động"),
    ("几", "jǐ", "mấy, bao nhiêu", "你有几个朋友？", "Nǐ yǒu jǐ ge péngyou?", "Bạn có mấy người bạn?", "Câu hỏi"),
    ("家", "jiā", "nhà, gia đình", "我家有三个人。", "Wǒ jiā yǒu sān ge rén.", "Nhà tôi có ba người.", "Gia đình"),
    ("叫", "jiào", "tên là; gọi", "我叫小明。", "Wǒ jiào Xiǎomíng.", "Tôi tên là Tiểu Minh.", "Con người"),
    ("今天", "jīntiān", "hôm nay", "今天是星期一。", "Jīntiān shì xīngqīyī.", "Hôm nay là thứ Hai.", "Ngày tháng"),
    ("九", "jiǔ", "chín", "现在九点。", "Xiànzài jiǔ diǎn.", "Bây giờ là chín giờ.", "Con số"),
    ("开", "kāi", "mở; lái", "请开门。", "Qǐng kāi mén.", "Vui lòng mở cửa.", "Hoạt động"),
    ("看", "kàn", "xem, nhìn", "我在看书。", "Wǒ zài kàn shū.", "Tôi đang đọc sách.", "Hoạt động"),
    ("看见", "kànjiàn", "nhìn thấy", "我看见老师了。", "Wǒ kànjiàn lǎoshī le.", "Tôi đã nhìn thấy giáo viên.", "Hoạt động"),
    ("块", "kuài", "đồng; miếng", "这个十块钱。", "Zhège shí kuài qián.", "Cái này giá mười đồng.", "Con số"),
    ("来", "lái", "đến", "你什么时候来？", "Nǐ shénme shíhou lái?", "Khi nào bạn đến?", "Hoạt động"),
    ("老师", "lǎoshī", "giáo viên", "她是我的汉语老师。", "Tā shì wǒ de Hànyǔ lǎoshī.", "Cô ấy là giáo viên tiếng Trung của tôi.", "Trường học"),
    ("了", "le", "rồi (trợ từ)", "我吃饭了。", "Wǒ chīfàn le.", "Tôi ăn cơm rồi.", "Đại từ"),
    ("冷", "lěng", "lạnh", "今天很冷。", "Jīntiān hěn lěng.", "Hôm nay rất lạnh.", "Tính chất"),
    ("里", "lǐ", "trong, bên trong", "书在桌子里。", "Shū zài zhuōzi lǐ.", "Sách ở trong bàn.", "Địa điểm"),
    ("六", "liù", "sáu", "我六点回家。", "Wǒ liù diǎn huí jiā.", "Tôi về nhà lúc sáu giờ.", "Con số"),
    ("妈妈", "māma", "mẹ", "妈妈在家。", "Māma zài jiā.", "Mẹ đang ở nhà.", "Gia đình"),
    ("吗", "ma", "không? (trợ từ nghi vấn)", "你是学生吗？", "Nǐ shì xuésheng ma?", "Bạn là học sinh phải không?", "Câu hỏi"),
    ("买", "mǎi", "mua", "我想买苹果。", "Wǒ xiǎng mǎi píngguǒ.", "Tôi muốn mua táo.", "Hoạt động"),
    ("猫", "māo", "con mèo", "我家有一只猫。", "Wǒ jiā yǒu yì zhī māo.", "Nhà tôi có một con mèo.", "Đồ vật"),
    ("没关系", "méi guānxi", "không sao", "没关系，你坐吧。", "Méi guānxi, nǐ zuò ba.", "Không sao, bạn ngồi đi.", "Chào hỏi"),
    ("没有", "méiyǒu", "không có", "我没有电脑。", "Wǒ méiyǒu diànnǎo.", "Tôi không có máy tính.", "Đại từ"),
    ("米饭", "mǐfàn", "cơm", "我中午吃米饭。", "Wǒ zhōngwǔ chī mǐfàn.", "Buổi trưa tôi ăn cơm.", "Ăn uống"),
    ("明天", "míngtiān", "ngày mai", "明天我去学校。", "Míngtiān wǒ qù xuéxiào.", "Ngày mai tôi đi học.", "Ngày tháng"),
    ("名字", "míngzi", "tên", "你的名字是什么？", "Nǐ de míngzi shì shénme?", "Tên của bạn là gì?", "Con người"),
    ("哪", "nǎ", "nào", "你喜欢哪个？", "Nǐ xǐhuan nǎge?", "Bạn thích cái nào?", "Câu hỏi"),
    ("哪儿", "nǎr", "ở đâu", "你住在哪儿？", "Nǐ zhù zài nǎr?", "Bạn sống ở đâu?", "Câu hỏi"),
    ("那", "nà", "kia, đó", "那是我的老师。", "Nà shì wǒ de lǎoshī.", "Đó là giáo viên của tôi.", "Đại từ"),
    ("呢", "ne", "thế còn...?", "我很好，你呢？", "Wǒ hěn hǎo, nǐ ne?", "Tôi khỏe, còn bạn?", "Câu hỏi"),
    ("能", "néng", "có thể", "你能来吗？", "Nǐ néng lái ma?", "Bạn có thể đến không?", "Hoạt động"),
    ("你", "nǐ", "bạn", "你叫什么名字？", "Nǐ jiào shénme míngzi?", "Bạn tên là gì?", "Đại từ"),
    ("年", "nián", "năm", "我在中国住了三年。", "Wǒ zài Zhōngguó zhù le sān nián.", "Tôi đã sống ở Trung Quốc ba năm.", "Ngày tháng"),
    ("女儿", "nǚ'ér", "con gái", "她女儿是学生。", "Tā nǚ'ér shì xuésheng.", "Con gái cô ấy là học sinh.", "Gia đình"),
    ("朋友", "péngyou", "bạn bè", "他是我的朋友。", "Tā shì wǒ de péngyou.", "Anh ấy là bạn của tôi.", "Con người"),
    ("漂亮", "piàoliang", "xinh đẹp", "这件衣服很漂亮。", "Zhè jiàn yīfu hěn piàoliang.", "Bộ quần áo này rất đẹp.", "Tính chất"),
    ("苹果", "píngguǒ", "quả táo", "我喜欢吃苹果。", "Wǒ xǐhuan chī píngguǒ.", "Tôi thích ăn táo.", "Ăn uống"),
    ("七", "qī", "bảy", "一个星期有七天。", "Yí ge xīngqī yǒu qī tiān.", "Một tuần có bảy ngày.", "Con số"),
    ("前面", "qiánmiàn", "phía trước", "商店在学校前面。", "Shāngdiàn zài xuéxiào qiánmiàn.", "Cửa hàng ở phía trước trường.", "Địa điểm"),
    ("钱", "qián", "tiền", "我没有钱。", "Wǒ méiyǒu qián.", "Tôi không có tiền.", "Đồ vật"),
    ("请", "qǐng", "mời, xin vui lòng", "请坐。", "Qǐng zuò.", "Mời ngồi.", "Chào hỏi"),
    ("去", "qù", "đi", "我下午去医院。", "Wǒ xiàwǔ qù yīyuàn.", "Buổi chiều tôi đi bệnh viện.", "Hoạt động"),
    ("热", "rè", "nóng", "今天太热了。", "Jīntiān tài rè le.", "Hôm nay nóng quá.", "Tính chất"),
    ("人", "rén", "người", "商店里有很多人。", "Shāngdiàn lǐ yǒu hěn duō rén.", "Trong cửa hàng có rất nhiều người.", "Con người"),
    ("认识", "rènshi", "quen, biết", "我认识那个医生。", "Wǒ rènshi nàge yīshēng.", "Tôi biết vị bác sĩ đó.", "Con người"),
    ("三", "sān", "ba", "我家有三个人。", "Wǒ jiā yǒu sān ge rén.", "Nhà tôi có ba người.", "Con số"),
    ("商店", "shāngdiàn", "cửa hàng", "我去商店买东西。", "Wǒ qù shāngdiàn mǎi dōngxi.", "Tôi đến cửa hàng mua đồ.", "Địa điểm"),
    ("上", "shàng", "trên; lên", "书在桌子上。", "Shū zài zhuōzi shàng.", "Sách ở trên bàn.", "Địa điểm"),
    ("上午", "shàngwǔ", "buổi sáng", "我上午学习汉语。", "Wǒ shàngwǔ xuéxí Hànyǔ.", "Buổi sáng tôi học tiếng Trung.", "Thời gian"),
    ("少", "shǎo", "ít", "杯子里的水很少。", "Bēizi lǐ de shuǐ hěn shǎo.", "Nước trong cốc rất ít.", "Tính chất"),
    ("谁", "shéi", "ai", "她是谁？", "Tā shì shéi?", "Cô ấy là ai?", "Câu hỏi"),
    ("什么", "shénme", "gì, cái gì", "你想吃什么？", "Nǐ xiǎng chī shénme?", "Bạn muốn ăn gì?", "Câu hỏi"),
    ("十", "shí", "mười", "我有十块钱。", "Wǒ yǒu shí kuài qián.", "Tôi có mười đồng.", "Con số"),
    ("时候", "shíhou", "lúc, khi", "你什么时候回家？", "Nǐ shénme shíhou huí jiā?", "Khi nào bạn về nhà?", "Thời gian"),
    ("是", "shì", "là", "我是越南人。", "Wǒ shì Yuènán rén.", "Tôi là người Việt Nam.", "Đại từ"),
    ("书", "shū", "sách", "这本书很好。", "Zhè běn shū hěn hǎo.", "Quyển sách này rất hay.", "Đồ vật"),
    ("水", "shuǐ", "nước", "我想喝水。", "Wǒ xiǎng hē shuǐ.", "Tôi muốn uống nước.", "Ăn uống"),
    ("水果", "shuǐguǒ", "hoa quả", "妈妈买了很多水果。", "Māma mǎi le hěn duō shuǐguǒ.", "Mẹ đã mua rất nhiều hoa quả.", "Ăn uống"),
    ("睡觉", "shuìjiào", "ngủ", "我十点睡觉。", "Wǒ shí diǎn shuìjiào.", "Tôi đi ngủ lúc mười giờ.", "Hoạt động"),
    ("说", "shuō", "nói", "老师在说汉语。", "Lǎoshī zài shuō Hànyǔ.", "Giáo viên đang nói tiếng Trung.", "Hoạt động"),
    ("四", "sì", "bốn", "桌子上有四个杯子。", "Zhuōzi shàng yǒu sì ge bēizi.", "Trên bàn có bốn cái cốc.", "Con số"),
    ("岁", "suì", "tuổi", "我女儿五岁。", "Wǒ nǚ'ér wǔ suì.", "Con gái tôi năm tuổi.", "Con số"),
    ("他", "tā", "anh ấy, ông ấy", "他是我同学。", "Tā shì wǒ tóngxué.", "Anh ấy là bạn học của tôi.", "Đại từ"),
    ("她", "tā", "cô ấy, bà ấy", "她在北京工作。", "Tā zài Běijīng gōngzuò.", "Cô ấy làm việc ở Bắc Kinh.", "Đại từ"),
    ("太", "tài", "quá, rất", "这个太大了。", "Zhège tài dà le.", "Cái này to quá.", "Tính chất"),
    ("天气", "tiānqì", "thời tiết", "今天天气怎么样？", "Jīntiān tiānqì zěnmeyàng?", "Thời tiết hôm nay thế nào?", "Ngày tháng"),
    ("听", "tīng", "nghe", "请听老师说。", "Qǐng tīng lǎoshī shuō.", "Hãy nghe giáo viên nói.", "Hoạt động"),
    ("同学", "tóngxué", "bạn học", "小明是我的同学。", "Xiǎomíng shì wǒ de tóngxué.", "Tiểu Minh là bạn học của tôi.", "Trường học"),
    ("喂", "wèi", "a lô", "喂，你好！", "Wèi, nǐ hǎo!", "A lô, xin chào!", "Chào hỏi"),
    ("我", "wǒ", "tôi", "我是学生。", "Wǒ shì xuésheng.", "Tôi là học sinh.", "Đại từ"),
    ("我们", "wǒmen", "chúng tôi, chúng ta", "我们一起学习。", "Wǒmen yìqǐ xuéxí.", "Chúng ta cùng học.", "Đại từ"),
    ("五", "wǔ", "năm", "现在五点。", "Xiànzài wǔ diǎn.", "Bây giờ là năm giờ.", "Con số"),
    ("喜欢", "xǐhuan", "thích", "我喜欢看电影。", "Wǒ xǐhuan kàn diànyǐng.", "Tôi thích xem phim.", "Hoạt động"),
    ("下", "xià", "dưới; xuống", "猫在桌子下。", "Māo zài zhuōzi xià.", "Con mèo ở dưới bàn.", "Địa điểm"),
    ("下午", "xiàwǔ", "buổi chiều", "我们下午去商店。", "Wǒmen xiàwǔ qù shāngdiàn.", "Buổi chiều chúng tôi đi cửa hàng.", "Thời gian"),
    ("下雨", "xiàyǔ", "mưa", "今天下雨了。", "Jīntiān xiàyǔ le.", "Hôm nay trời mưa.", "Ngày tháng"),
    ("先生", "xiānsheng", "ông, ngài", "王先生是医生。", "Wáng xiānsheng shì yīshēng.", "Ông Vương là bác sĩ.", "Con người"),
    ("现在", "xiànzài", "bây giờ", "现在几点？", "Xiànzài jǐ diǎn?", "Bây giờ là mấy giờ?", "Thời gian"),
    ("想", "xiǎng", "muốn; nghĩ", "我想喝茶。", "Wǒ xiǎng hē chá.", "Tôi muốn uống trà.", "Hoạt động"),
    ("小", "xiǎo", "nhỏ", "这只猫很小。", "Zhè zhī māo hěn xiǎo.", "Con mèo này rất nhỏ.", "Tính chất"),
    ("小姐", "xiǎojiě", "cô, tiểu thư", "小姐，请问您叫什么？", "Xiǎojiě, qǐngwèn nín jiào shénme?", "Thưa cô, xin hỏi cô tên gì?", "Con người"),
    ("些", "xiē", "một vài", "我买了一些苹果。", "Wǒ mǎi le yìxiē píngguǒ.", "Tôi đã mua vài quả táo.", "Con số"),
    ("写", "xiě", "viết", "我会写汉字。", "Wǒ huì xiě Hànzì.", "Tôi biết viết chữ Hán.", "Hoạt động"),
    ("谢谢", "xièxie", "cảm ơn", "谢谢你的帮助。", "Xièxie nǐ de bāngzhù.", "Cảm ơn sự giúp đỡ của bạn.", "Chào hỏi"),
    ("星期", "xīngqī", "tuần, thứ", "今天星期几？", "Jīntiān xīngqī jǐ?", "Hôm nay là thứ mấy?", "Ngày tháng"),
    ("学生", "xuésheng", "học sinh", "我是汉语学生。", "Wǒ shì Hànyǔ xuésheng.", "Tôi là học viên tiếng Trung.", "Trường học"),
    ("学习", "xuéxí", "học tập", "我每天学习汉语。", "Wǒ měitiān xuéxí Hànyǔ.", "Mỗi ngày tôi học tiếng Trung.", "Trường học"),
    ("学校", "xuéxiào", "trường học", "我的学校很大。", "Wǒ de xuéxiào hěn dà.", "Trường của tôi rất lớn.", "Trường học"),
    ("一", "yī", "một", "我有一个杯子。", "Wǒ yǒu yí ge bēizi.", "Tôi có một cái cốc.", "Con số"),
    ("一点儿", "yìdiǎnr", "một chút", "我想喝一点儿水。", "Wǒ xiǎng hē yìdiǎnr shuǐ.", "Tôi muốn uống một chút nước.", "Con số"),
    ("衣服", "yīfu", "quần áo", "我买了新衣服。", "Wǒ mǎi le xīn yīfu.", "Tôi đã mua quần áo mới.", "Đồ vật"),
    ("医生", "yīshēng", "bác sĩ", "她是医院的医生。", "Tā shì yīyuàn de yīshēng.", "Cô ấy là bác sĩ của bệnh viện.", "Công việc"),
    ("医院", "yīyuàn", "bệnh viện", "医院在学校后面。", "Yīyuàn zài xuéxiào hòumiàn.", "Bệnh viện ở phía sau trường.", "Địa điểm"),
    ("椅子", "yǐzi", "cái ghế", "请坐在椅子上。", "Qǐng zuò zài yǐzi shàng.", "Mời ngồi lên ghế.", "Đồ vật"),
    ("有", "yǒu", "có", "桌子上有一本书。", "Zhuōzi shàng yǒu yì běn shū.", "Trên bàn có một quyển sách.", "Đại từ"),
    ("月", "yuè", "tháng", "现在是五月。", "Xiànzài shì wǔ yuè.", "Bây giờ là tháng Năm.", "Ngày tháng"),
    ("再见", "zàijiàn", "tạm biệt", "老师，再见！", "Lǎoshī, zàijiàn!", "Tạm biệt thầy/cô!", "Chào hỏi"),
    ("在", "zài", "ở, tại; đang", "我在学校学习。", "Wǒ zài xuéxiào xuéxí.", "Tôi học ở trường.", "Địa điểm"),
    ("怎么", "zěnme", "thế nào, làm sao", "这个字怎么读？", "Zhège zì zěnme dú?", "Chữ này đọc thế nào?", "Câu hỏi"),
    ("怎么样", "zěnmeyàng", "thế nào", "这本书怎么样？", "Zhè běn shū zěnmeyàng?", "Quyển sách này thế nào?", "Câu hỏi"),
    ("这", "zhè", "này, đây", "这是我的杯子。", "Zhè shì wǒ de bēizi.", "Đây là cốc của tôi.", "Đại từ"),
    ("中国", "Zhōngguó", "Trung Quốc", "我想去中国。", "Wǒ xiǎng qù Zhōngguó.", "Tôi muốn đi Trung Quốc.", "Địa điểm"),
    ("中午", "zhōngwǔ", "buổi trưa", "我们中午吃米饭。", "Wǒmen zhōngwǔ chī mǐfàn.", "Buổi trưa chúng tôi ăn cơm.", "Thời gian"),
    ("住", "zhù", "sống, ở", "你住在哪儿？", "Nǐ zhù zài nǎr?", "Bạn sống ở đâu?", "Hoạt động"),
    ("桌子", "zhuōzi", "cái bàn", "电脑在桌子上。", "Diànnǎo zài zhuōzi shàng.", "Máy tính ở trên bàn.", "Đồ vật"),
    ("字", "zì", "chữ", "这个字怎么写？", "Zhège zì zěnme xiě?", "Chữ này viết thế nào?", "Trường học"),
    ("昨天", "zuótiān", "hôm qua", "昨天我去了医院。", "Zuótiān wǒ qù le yīyuàn.", "Hôm qua tôi đã đi bệnh viện.", "Ngày tháng"),
    ("坐", "zuò", "ngồi; đi bằng", "请坐这儿。", "Qǐng zuò zhèr.", "Mời ngồi ở đây.", "Hoạt động"),
    ("做", "zuò", "làm", "你在做什么？", "Nǐ zài zuò shénme?", "Bạn đang làm gì?", "Hoạt động"),
]


# hanzi, pinyin, meaning, topic, ordered Hanzi chunks, matching pinyin chunks
HSK1_SENTENCES = [
    ("我是学生。", "Wǒ shì xuésheng.", "Tôi là học sinh.", "Trường học", ["我", "是", "学生"], ["wǒ", "shì", "xuésheng"]),
    ("她是我的汉语老师。", "Tā shì wǒ de Hànyǔ lǎoshī.", "Cô ấy là giáo viên tiếng Trung của tôi.", "Trường học", ["她", "是", "我", "的", "汉语", "老师"], ["tā", "shì", "wǒ", "de", "Hànyǔ", "lǎoshī"]),
    ("我们都喜欢学习汉语。", "Wǒmen dōu xǐhuan xuéxí Hànyǔ.", "Chúng tôi đều thích học tiếng Trung.", "Trường học", ["我们", "都", "喜欢", "学习", "汉语"], ["wǒmen", "dōu", "xǐhuan", "xuéxí", "Hànyǔ"]),
    ("你叫什么名字？", "Nǐ jiào shénme míngzi?", "Bạn tên là gì?", "Chào hỏi", ["你", "叫", "什么", "名字"], ["nǐ", "jiào", "shénme", "míngzi"]),
    ("你住在哪儿？", "Nǐ zhù zài nǎr?", "Bạn sống ở đâu?", "Câu hỏi", ["你", "住", "在", "哪儿"], ["nǐ", "zhù", "zài", "nǎr"]),
    ("我家有三个人。", "Wǒ jiā yǒu sān ge rén.", "Nhà tôi có ba người.", "Gia đình", ["我家", "有", "三", "个", "人"], ["wǒ jiā", "yǒu", "sān", "ge", "rén"]),
    ("我爸爸在医院工作。", "Wǒ bàba zài yīyuàn gōngzuò.", "Bố tôi làm việc ở bệnh viện.", "Công việc", ["我", "爸爸", "在", "医院", "工作"], ["wǒ", "bàba", "zài", "yīyuàn", "gōngzuò"]),
    ("妈妈去商店买水果。", "Māma qù shāngdiàn mǎi shuǐguǒ.", "Mẹ đi cửa hàng mua hoa quả.", "Hoạt động", ["妈妈", "去", "商店", "买", "水果"], ["māma", "qù", "shāngdiàn", "mǎi", "shuǐguǒ"]),
    ("我想喝一点儿水。", "Wǒ xiǎng hē yìdiǎnr shuǐ.", "Tôi muốn uống một chút nước.", "Ăn uống", ["我", "想", "喝", "一点儿", "水"], ["wǒ", "xiǎng", "hē", "yìdiǎnr", "shuǐ"]),
    ("你喜欢吃苹果吗？", "Nǐ xǐhuan chī píngguǒ ma?", "Bạn có thích ăn táo không?", "Ăn uống", ["你", "喜欢", "吃", "苹果", "吗"], ["nǐ", "xǐhuan", "chī", "píngguǒ", "ma"]),
    ("杯子里有茶。", "Bēizi lǐ yǒu chá.", "Trong cốc có trà.", "Ăn uống", ["杯子", "里", "有", "茶"], ["bēizi", "lǐ", "yǒu", "chá"]),
    ("桌子上有一本书。", "Zhuōzi shàng yǒu yì běn shū.", "Trên bàn có một quyển sách.", "Đồ vật", ["桌子", "上", "有", "一", "本", "书"], ["zhuōzi", "shàng", "yǒu", "yì", "běn", "shū"]),
    ("猫在椅子下。", "Māo zài yǐzi xià.", "Con mèo ở dưới ghế.", "Địa điểm", ["猫", "在", "椅子", "下"], ["māo", "zài", "yǐzi", "xià"]),
    ("今天是星期一。", "Jīntiān shì xīngqīyī.", "Hôm nay là thứ Hai.", "Ngày tháng", ["今天", "是", "星期一"], ["jīntiān", "shì", "xīngqīyī"]),
    ("现在是上午九点。", "Xiànzài shì shàngwǔ jiǔ diǎn.", "Bây giờ là chín giờ sáng.", "Thời gian", ["现在", "是", "上午", "九", "点"], ["xiànzài", "shì", "shàngwǔ", "jiǔ", "diǎn"]),
    ("明天下午我去北京。", "Míngtiān xiàwǔ wǒ qù Běijīng.", "Chiều mai tôi đi Bắc Kinh.", "Ngày tháng", ["明天", "下午", "我", "去", "北京"], ["míngtiān", "xiàwǔ", "wǒ", "qù", "Běijīng"]),
    ("昨天天气很冷。", "Zuótiān tiānqì hěn lěng.", "Hôm qua thời tiết rất lạnh.", "Ngày tháng", ["昨天", "天气", "很", "冷"], ["zuótiān", "tiānqì", "hěn", "lěng"]),
    ("今天下雨了。", "Jīntiān xiàyǔ le.", "Hôm nay trời mưa rồi.", "Ngày tháng", ["今天", "下雨", "了"], ["jīntiān", "xiàyǔ", "le"]),
    ("商店在学校前面。", "Shāngdiàn zài xuéxiào qiánmiàn.", "Cửa hàng ở phía trước trường học.", "Địa điểm", ["商店", "在", "学校", "前面"], ["shāngdiàn", "zài", "xuéxiào", "qiánmiàn"]),
    ("饭店在医院后面。", "Fàndiàn zài yīyuàn hòumiàn.", "Nhà hàng ở phía sau bệnh viện.", "Địa điểm", ["饭店", "在", "医院", "后面"], ["fàndiàn", "zài", "yīyuàn", "hòumiàn"]),
    ("我坐出租车去学校。", "Wǒ zuò chūzūchē qù xuéxiào.", "Tôi đi taxi đến trường.", "Địa điểm", ["我", "坐", "出租车", "去", "学校"], ["wǒ", "zuò", "chūzūchē", "qù", "xuéxiào"]),
    ("他会说汉语。", "Tā huì shuō Hànyǔ.", "Anh ấy biết nói tiếng Trung.", "Hoạt động", ["他", "会", "说", "汉语"], ["tā", "huì", "shuō", "Hànyǔ"]),
    ("请坐在椅子上。", "Qǐng zuò zài yǐzi shàng.", "Mời ngồi trên ghế.", "Chào hỏi", ["请", "坐", "在", "椅子", "上"], ["qǐng", "zuò", "zài", "yǐzi", "shàng"]),
    ("老师在看书。", "Lǎoshī zài kàn shū.", "Giáo viên đang đọc sách.", "Trường học", ["老师", "在", "看", "书"], ["lǎoshī", "zài", "kàn", "shū"]),
    ("我们去看电影。", "Wǒmen qù kàn diànyǐng.", "Chúng ta đi xem phim.", "Hoạt động", ["我们", "去", "看", "电影"], ["wǒmen", "qù", "kàn", "diànyǐng"]),
    ("这个苹果很大。", "Zhège píngguǒ hěn dà.", "Quả táo này rất to.", "Tính chất", ["这个", "苹果", "很", "大"], ["zhège", "píngguǒ", "hěn", "dà"]),
    ("这些衣服很漂亮。", "Zhèxiē yīfu hěn piàoliang.", "Những bộ quần áo này rất đẹp.", "Tính chất", ["这些", "衣服", "很", "漂亮"], ["zhèxiē", "yīfu", "hěn", "piàoliang"]),
    ("认识你很高兴。", "Rènshi nǐ hěn gāoxìng.", "Rất vui được biết bạn.", "Chào hỏi", ["认识", "你", "很", "高兴"], ["rènshi", "nǐ", "hěn", "gāoxìng"]),
    ("对不起，我不认识他。", "Duìbuqǐ, wǒ bù rènshi tā.", "Xin lỗi, tôi không biết anh ấy.", "Chào hỏi", ["对不起", "我", "不", "认识", "他"], ["duìbuqǐ", "wǒ", "bù", "rènshi", "tā"]),
    ("谢谢你的茶。", "Xièxie nǐ de chá.", "Cảm ơn trà của bạn.", "Chào hỏi", ["谢谢", "你", "的", "茶"], ["xièxie", "nǐ", "de", "chá"]),
]


INSERT_SQL = """
INSERT INTO vocabulary (
    hanzi, pinyin, meaning, example, example_pinyin, example_meaning,
    topic, created_at, updated_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(hanzi) DO NOTHING
"""

SENTENCE_INSERT_SQL = """
INSERT INTO sentences (
    hanzi, pinyin, meaning, topic, tokens_json, pinyin_tokens_json,
    created_at, updated_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(hanzi) DO NOTHING
"""


FULL_LEVEL_FILES = ["hsk_1.json", "hsk_2.json", "hsk_3.json", "hsk_4.json", "hsk_5.json", "hsk_6.json", "hsk_7_9.json"]


def _full_data_dir() -> Path:
    """Locate the HSK 1-9 JSON dataset in both source and packaged builds.

    PyInstaller unpacks bundled data under ``sys._MEIPASS`` rather than next to
    the script, so resolving this relative to ``__file__`` alone made the
    packaged app silently fall back to the 150 curated HSK1 words.
    """
    candidates = [Path(__file__).resolve().parent / "data"]
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir:
        candidates.insert(0, Path(bundle_dir) / "scripts" / "data")
        candidates.insert(1, Path(bundle_dir) / "data")
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return candidates[-1]


FULL_DATA_DIR = _full_data_dir()

FULL_UPSERT_SQL = """
INSERT INTO vocabulary (
    hanzi, pinyin, meaning, meaning_en, traditional, pos, pos_vi,
    classifiers, frequency, hsk_level, created_at, updated_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(hanzi) DO UPDATE SET
    meaning = CASE
        WHEN vocabulary.meaning IS NULL OR vocabulary.meaning = vocabulary.meaning_en
        THEN excluded.meaning
        ELSE vocabulary.meaning
    END,
    meaning_en = excluded.meaning_en,
    traditional = excluded.traditional,
    pos = excluded.pos,
    pos_vi = excluded.pos_vi,
    classifiers = excluded.classifiers,
    frequency = excluded.frequency,
    hsk_level = excluded.hsk_level,
    updated_at = excluded.updated_at
"""


def _load_full_level_records() -> list[dict]:
    records: list[dict] = []
    for filename in FULL_LEVEL_FILES:
        path = FULL_DATA_DIR / filename
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as handle:
            records.extend(json.load(handle))
    return records


def _repair_legacy_meanings(connection, records: list[dict], now: str) -> int:
    """Replace stored meanings that older builds left in English.

    Until the CVDICT import, roughly 7.000 words carried their English gloss in
    the Vietnamese ``meaning`` column. `FULL_UPSERT_SQL` only overwrites the
    exact case where ``meaning`` equals ``meaning_en``; the many rows holding a
    *slice* of the English text ("you" against "you (informal, as opposed to
    courteous 您)"), mojibake, or the headword echoed back would otherwise keep
    showing English forever in a database that already exists.

    A second class of correction goes through here too. `scripts/repair_meanings.py`
    fixes dataset entries that read as fluent Vietnamese while meaning the wrong
    thing — 少见 defined as "nhìn". Those pass `is_english_gloss` happily, so
    without a second rule an installed database would keep the wrong gloss
    forever no matter how often the dataset is corrected.

    Hand-written Vietnamese is still preserved. The curated HSK 1 glosses are
    tuned for beginners and deliberately narrower than the dictionary's, so they
    are exempt; for every other word the shipped dataset is authoritative.
    """
    replacements = {
        record["hanzi"]: record["meaning"]
        for record in records
        if record.get("meaning_is_vietnamese") and record.get("meaning")
    }
    if not replacements:
        return 0

    curated = {record[0] for record in HSK1_VOCABULARY}
    rows = connection.execute(
        "SELECT id, hanzi, meaning, meaning_en FROM vocabulary"
    ).fetchall()
    repaired = 0
    for row in rows:
        replacement = replacements.get(row["hanzi"])
        if not replacement or replacement == row["meaning"]:
            continue
        stored = repair_mojibake(row["meaning"] or "")
        # Curated words keep their beginner-tuned gloss — but only while that
        # gloss is usable Vietnamese. One left in English is still repaired.
        if row["hanzi"] in curated and not is_english_gloss(
            stored, row["meaning_en"], row["hanzi"]
        ):
            continue
        connection.execute(
            "UPDATE vocabulary SET meaning = ?, updated_at = ? WHERE id = ?",
            (replacement, now, row["id"]),
        )
        repaired += 1
    return repaired


def seed_full_vocabulary(return_details: bool = False) -> int | dict[str, int]:
    """Insert/refresh the full HSK 1-9 dataset without touching curated meanings."""
    initialize_database()
    now = utc_now()
    records = _load_full_level_records()
    added = 0
    repaired = 0
    with get_connection() as connection:
        for record in records:
            cursor = connection.execute(
                FULL_UPSERT_SQL,
                (
                    record["hanzi"],
                    record["pinyin"],
                    record["meaning"],
                    record["meaning_en"],
                    record.get("traditional"),
                    json.dumps(record.get("pos") or [], ensure_ascii=False),
                    json.dumps(record.get("pos_vi") or [], ensure_ascii=False),
                    json.dumps(record.get("classifiers") or [], ensure_ascii=False),
                    record.get("frequency"),
                    record["hsk_level"],
                    now,
                    now,
                ),
            )
            added += max(cursor.rowcount, 0)
        repaired = _repair_legacy_meanings(connection, records, now)
        connection.execute(
            """
            INSERT OR IGNORE INTO learning_progress (
                vocabulary_id, status, review_count, correct_count,
                incorrect_count, created_at, updated_at
            )
            SELECT id, 'new', 0, 0, 0, ?, ? FROM vocabulary
            """,
            (now, now),
        )
    if return_details:
        return {
            "vocabulary_upserted": added,
            "meanings_repaired": repaired,
            "total_records": len(records),
        }
    return added


LEVELED_SENTENCE_FILE = "sentences.json"

LEVELED_SENTENCE_SQL = """
INSERT INTO sentences (
    hanzi, pinyin, meaning, topic, tokens_json, pinyin_tokens_json,
    hsk_level, difficulty, created_at, updated_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(hanzi) DO UPDATE SET
    hsk_level = excluded.hsk_level,
    difficulty = excluded.difficulty,
    updated_at = excluded.updated_at
"""


def seed_leveled_sentences() -> int:
    """Load the HSK-tagged sentence corpus used by the rearrange exercise.

    Sentences arrive pre-segmented as ``[hanzi, pinyin]`` token pairs, so the
    exercise never has to guess word boundaries -- a wrong split would make a
    correct answer look wrong.
    """
    path = FULL_DATA_DIR / LEVELED_SENTENCE_FILE
    if not path.exists():
        return 0
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)

    now = utc_now()
    added = 0
    with get_connection() as connection:
        for entry in payload.get("sentences", []):
            tokens = entry.get("tokens") or []
            if not tokens:
                continue
            hanzi_tokens = [pair[0] for pair in tokens]
            pinyin_tokens = [pair[1] for pair in tokens]
            hanzi = "".join(hanzi_tokens)
            # Punctuation attaches to the preceding syllable rather than taking
            # its own space, so the rendered pinyin reads naturally.
            pinyin_parts: list[str] = []
            for token, reading in zip(hanzi_tokens, pinyin_tokens):
                if token in "，。？！、；：":
                    if pinyin_parts:
                        pinyin_parts[-1] += reading
                    else:
                        pinyin_parts.append(reading)
                else:
                    pinyin_parts.append(reading)
            cursor = connection.execute(
                LEVELED_SENTENCE_SQL,
                (
                    hanzi,
                    " ".join(pinyin_parts),
                    entry["meaning"],
                    entry.get("topic"),
                    json.dumps(hanzi_tokens, ensure_ascii=False),
                    json.dumps(pinyin_tokens, ensure_ascii=False),
                    str(entry.get("level", "1")),
                    len(hanzi_tokens),
                    now,
                    now,
                ),
            )
            added += max(cursor.rowcount, 0)
    return added


GRAMMAR_FILE = "grammar.json"

GRAMMAR_SQL = """
    INSERT INTO grammar_points (
        code, hsk_level, title_vi, pattern_zh, summary_vi, explanation_vi,
        pitfall_vi, examples_json, exercises_json, sort_order, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(code) DO UPDATE SET
        hsk_level = excluded.hsk_level,
        title_vi = excluded.title_vi,
        pattern_zh = excluded.pattern_zh,
        summary_vi = excluded.summary_vi,
        explanation_vi = excluded.explanation_vi,
        pitfall_vi = excluded.pitfall_vi,
        examples_json = excluded.examples_json,
        exercises_json = excluded.exercises_json,
        sort_order = excluded.sort_order,
        updated_at = excluded.updated_at
"""


def seed_grammar() -> int:
    """Load the grammar lessons, updating the text of ones already present.

    Upserts rather than inserts so a corrected explanation reaches an installed
    database. The learner's progress lives in `grammar_progress`, keyed by id,
    and is never touched here.
    """
    path = FULL_DATA_DIR / GRAMMAR_FILE
    if not path.exists():
        return 0
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)

    now = utc_now()
    points = payload.get("points", [])
    with get_connection() as connection:
        for order, point in enumerate(points):
            connection.execute(
                GRAMMAR_SQL,
                (
                    point["code"],
                    str(point.get("hsk_level", "1")),
                    point["title_vi"],
                    point.get("pattern_zh", ""),
                    point.get("summary_vi", ""),
                    point.get("explanation_vi", ""),
                    point.get("pitfall_vi", ""),
                    json.dumps(point.get("examples", []), ensure_ascii=False),
                    json.dumps(point.get("exercises", []), ensure_ascii=False),
                    order,
                    now,
                    now,
                ),
            )
    return len(points)


CHARACTER_FILE = "characters.json"

CHARACTER_SQL = """
    INSERT INTO characters (
        hanzi, pinyin, han_viet, han_viet_source, meaning_vi, meaning_en,
        traditional, stroke_count, radical_number, radicals_json,
        mnemonic_vi, stroke_hint_vi, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(hanzi) DO UPDATE SET
        pinyin = excluded.pinyin,
        han_viet = excluded.han_viet,
        han_viet_source = excluded.han_viet_source,
        meaning_vi = excluded.meaning_vi,
        meaning_en = excluded.meaning_en,
        traditional = excluded.traditional,
        stroke_count = excluded.stroke_count,
        radical_number = excluded.radical_number,
        radicals_json = excluded.radicals_json,
        mnemonic_vi = excluded.mnemonic_vi,
        stroke_hint_vi = excluded.stroke_hint_vi,
        updated_at = excluded.updated_at
"""

RADICAL_SQL = """
    INSERT INTO radicals (hanzi, name_vi, meaning_vi, mnemonic_vi, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(hanzi) DO UPDATE SET
        name_vi = excluded.name_vi,
        meaning_vi = excluded.meaning_vi,
        mnemonic_vi = excluded.mnemonic_vi,
        updated_at = excluded.updated_at
"""

_CJK = re.compile(r"[一-鿿]")


def seed_characters() -> dict[str, int]:
    """Load the character layer and wire it to the words that use it.

    Three things happen here, and the last two are the ones that make the
    feature possible at all:

    1. Upsert every character and radical from ``characters.json``. Same
       contract as the grammar seeder: content is replaced, learner state in
       `character_progress` is never touched.
    2. Rebuild `word_characters`, the word ↔ character index. This is what
       turns "show me every word built on 学" from a full-table LIKE scan into
       an indexed lookup, and it is the query behind the word-family screen.
    3. Derive, per character, the lowest HSK band it appears in and how many
       bank words use it — so "which characters unlock the most vocabulary"
       is an ORDER BY — and spell out each word in âm Hán-Việt.
    """
    path = FULL_DATA_DIR / CHARACTER_FILE
    if not path.exists():
        return {"characters": 0, "radicals": 0, "links": 0, "words_transcribed": 0}
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)

    now = utc_now()
    characters = payload.get("characters", [])
    radicals = payload.get("radicals", [])

    with get_connection() as connection:
        for entry in characters:
            connection.execute(
                CHARACTER_SQL,
                (
                    entry["hanzi"],
                    entry.get("pinyin", "") or "",
                    entry.get("han_viet", "") or "",
                    entry.get("han_viet_source", "") or "",
                    entry.get("meaning_vi", "") or "",
                    entry.get("meaning_en", "") or "",
                    entry.get("traditional"),
                    entry.get("stroke_count"),
                    entry.get("radical_number"),
                    json.dumps(entry.get("radicals", []), ensure_ascii=False),
                    entry.get("mnemonic_vi", "") or "",
                    entry.get("stroke_hint_vi", "") or "",
                    now,
                    now,
                ),
            )
        for radical in radicals:
            connection.execute(
                RADICAL_SQL,
                (
                    radical["hanzi"],
                    radical.get("name_vi", ""),
                    radical.get("meaning_vi", ""),
                    radical.get("mnemonic_vi", ""),
                    now,
                    now,
                ),
            )

        # --- link words to characters -----------------------------------
        words = connection.execute("SELECT id, hanzi FROM vocabulary").fetchall()
        readings = {
            row["hanzi"]: row["han_viet"]
            for row in connection.execute(
                "SELECT hanzi, han_viet FROM characters WHERE han_viet <> ''"
            )
        }
        links: list[tuple[int, int, str]] = []
        transcriptions: list[tuple[str, int]] = []
        for row in words:
            positions = [
                (index, char)
                for index, char in enumerate(row["hanzi"])
                if _CJK.match(char)
            ]
            links.extend((row["id"], index, char) for index, char in positions)
            syllables = [readings.get(char) for _, char in positions]
            # All or nothing: "đồ thư ?" reads as a bug, and a partial
            # transcription is exactly the case where a learner would trust a
            # reading that is not there.
            if syllables and all(syllables):
                transcriptions.append((" ".join(syllables), row["id"]))

        connection.execute("DELETE FROM word_characters")
        connection.executemany(
            "INSERT INTO word_characters (vocabulary_id, position, hanzi) VALUES (?, ?, ?)",
            links,
        )
        connection.executemany(
            "UPDATE vocabulary SET han_viet = ? WHERE id = ?", transcriptions
        )

        # --- derive per-character reach ----------------------------------
        # `hsk_level` here is the earliest band a character is met in, which is
        # the order a learner should meet the characters themselves.
        connection.execute(
            """
            UPDATE characters SET
                word_count = COALESCE((
                    SELECT COUNT(DISTINCT wc.vocabulary_id)
                    FROM word_characters wc WHERE wc.hanzi = characters.hanzi
                ), 0),
                hsk_level = (
                    SELECT v.hsk_level
                    FROM word_characters wc
                    JOIN vocabulary v ON v.id = wc.vocabulary_id
                    WHERE wc.hanzi = characters.hanzi
                    ORDER BY CASE v.hsk_level
                        WHEN '1' THEN 1 WHEN '2' THEN 2 WHEN '3' THEN 3
                        WHEN '4' THEN 4 WHEN '5' THEN 5 WHEN '6' THEN 6
                        ELSE 7 END
                    LIMIT 1
                )
            """
        )

    return {
        "characters": len(characters),
        "radicals": len(radicals),
        "links": len(links),
        "words_transcribed": len(transcriptions),
    }


def seed_database(return_details: bool = False) -> int | dict[str, int]:
    """Insert missing vocabulary and progress rows, preserving existing data."""
    initialize_database()
    now = utc_now()
    added = 0
    sentence_added = 0
    with get_connection() as connection:
        for record in HSK1_VOCABULARY:
            cursor = connection.execute(INSERT_SQL, (*record, now, now))
            added += max(cursor.rowcount, 0)
        connection.execute(
            """
            INSERT OR IGNORE INTO learning_progress (
                vocabulary_id, status, review_count, correct_count,
                incorrect_count, created_at, updated_at
            )
            SELECT id, 'new', 0, 0, 0, ?, ? FROM vocabulary
            """,
            (now, now),
        )
        for hanzi, pinyin, meaning, topic, tokens, pinyin_tokens in HSK1_SENTENCES:
            cursor = connection.execute(
                SENTENCE_INSERT_SQL,
                (
                    hanzi,
                    pinyin,
                    meaning,
                    topic,
                    json.dumps(tokens, ensure_ascii=False),
                    json.dumps(pinyin_tokens, ensure_ascii=False),
                    now,
                    now,
                ),
            )
            sentence_added += max(cursor.rowcount, 0)
    full_result = seed_full_vocabulary(return_details=True)
    leveled_sentences = seed_leveled_sentences()
    grammar_points = seed_grammar()
    # Last, because it indexes the vocabulary the steps above just wrote.
    characters = seed_characters()
    if return_details:
        return {
            "vocabulary_added": added,
            "sentences_added": sentence_added,
            "full_vocabulary_upserted": full_result["vocabulary_upserted"],
            "meanings_repaired": full_result["meanings_repaired"],
            "leveled_sentences_added": leveled_sentences,
            "grammar_points": grammar_points,
            "characters": characters["characters"],
            "radicals": characters["radicals"],
            "word_character_links": characters["links"],
            "words_transcribed": characters["words_transcribed"],
        }
    return added


def main() -> None:
    result = seed_database(return_details=True)
    print(
        f"Added {result['vocabulary_added']} curated vocabulary records and "
        f"{result['sentences_added']} sentence records. "
        f"Upserted {result['full_vocabulary_upserted']} full HSK 1-9 vocabulary records "
        f"and repaired {result['meanings_repaired']} English/mojibake meanings. "
        f"Seeded {result['grammar_points']} grammar points. "
        f"Seeded {result['characters']} characters and {result['radicals']} radicals, "
        f"linked {result['word_character_links']} word-character pairs and "
        f"transcribed {result['words_transcribed']} words into âm Hán-Việt. "
        f"Seed totals: {len(HSK1_VOCABULARY)} curated words, {len(HSK1_SENTENCES)} sentences."
    )


if __name__ == "__main__":
    main()
