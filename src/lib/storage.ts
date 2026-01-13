import fs from 'fs/promises';
import path from 'path';

const UPLOAD_DIR = path.join(process.cwd(), 'uploads');

export async function ensureUploadDir() {
  try {
    await fs.access(UPLOAD_DIR);
  } catch {
    await fs.mkdir(UPLOAD_DIR, { recursive: true });
  }
}

export async function saveFile(buffer: Buffer, filename: string, subfolder: string = ''): Promise<string> {
  await ensureUploadDir();

  const targetDir = subfolder ? path.join(UPLOAD_DIR, subfolder) : UPLOAD_DIR;

  try {
    await fs.access(targetDir);
  } catch {
    await fs.mkdir(targetDir, { recursive: true });
  }

  const filePath = path.join(targetDir, filename);
  await fs.writeFile(filePath, buffer);

  return subfolder ? `/uploads/${subfolder}/${filename}` : `/uploads/${filename}`;
}

export async function deleteFile(filePath: string): Promise<void> {
  try {
    const fullPath = path.join(process.cwd(), 'public', filePath);
    await fs.unlink(fullPath);
  } catch (error) {
    console.error('Error deleting file:', error);
  }
}
