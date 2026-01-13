import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const appointment = await prisma.appointment.findUnique({
      where: { id: params.id },
      include: {
        audioRecordings: true,
        photos: true,
        transcription: true,
      },
    });

    if (!appointment) {
      return NextResponse.json(
        { error: 'Termin nicht gefunden' },
        { status: 404 }
      );
    }

    return NextResponse.json(appointment);
  } catch (error) {
    console.error('Error fetching appointment:', error);
    return NextResponse.json(
      { error: 'Fehler beim Abrufen des Termins' },
      { status: 500 }
    );
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    await prisma.appointment.delete({
      where: { id: params.id },
    });

    return NextResponse.json({ message: 'Termin gelöscht' });
  } catch (error) {
    console.error('Error deleting appointment:', error);
    return NextResponse.json(
      { error: 'Fehler beim Löschen des Termins' },
      { status: 500 }
    );
  }
}
