import { useTranslation } from 'react-i18next';
import { ButtonLink, Card, EmptyState } from '../ui/primitives';

export function NotFound() {
  const { t } = useTranslation();
  return (
    <Card pad>
      <EmptyState title={t('notFound.title')} body={t('notFound.body')} action={<ButtonLink to="/">{t('notFound.home')}</ButtonLink>} />
    </Card>
  );
}
