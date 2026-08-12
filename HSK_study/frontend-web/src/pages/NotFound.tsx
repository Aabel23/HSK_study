import { Link } from "react-router-dom";
import { Button, Card } from "../components/ui";
import { IconHome } from "../components/icons";

export default function NotFound() {
  return (
    <Card className="mx-auto mt-10 flex max-w-lg flex-col items-center gap-3 px-6 py-16 text-center">
      <p className="hanzi text-6xl font-bold text-accent">迷路</p>
      <h1 className="font-display text-xl font-bold text-ink">Không tìm thấy trang</h1>
      <p className="max-w-sm text-sm text-ink-soft">
        Đường dẫn bạn mở không tồn tại. Hãy quay lại bảng điều khiển để tiếp tục học.
      </p>
      <Link to="/">
        <Button>
          <IconHome className="h-4 w-4" /> Về trang tổng quan
        </Button>
      </Link>
    </Card>
  );
}
