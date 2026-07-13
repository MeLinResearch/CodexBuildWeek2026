import { Badge } from '@/components/ui/badge';

interface IStatusChipProps {
  status: string;
}

const StatusChip = ({ status }: IStatusChipProps) => {
  return <Badge variant="outline">{status.replaceAll('_', ' ')}</Badge>;
};

export { StatusChip };
